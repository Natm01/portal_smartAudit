# procesos_estructura/feature_processor.py
import re
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    """Tipos de estructura de documento"""
    HEADER_DATA = "header_data"
    PARENT_CHILD = "parent_child"


@dataclass
class FeatureConfig:
    """Configuración de features según el tipo de documento"""
    doc_type: DocumentType
    enable_structural: bool = True
    enable_accounting: bool = True
    enable_keywords: bool = True
    enable_contextual: bool = True
    enable_pattern: bool = True


class DocumentFeatureExtractor:
    """Extractor optimizado de features para libros diarios contables"""
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig(DocumentType.HEADER_DATA)
        self.label_encoder = LabelEncoder()
        self._init_patterns()
        self._init_keywords()
    
    def _init_patterns(self):
        """Inicializa patrones de regex específicos de libros diarios"""
        self.patterns = {
            # Patrones estructurales
            'separator': re.compile(r"^\s*[-=\.*]{8,}\s*$"),
            
            # Patrones contables
            'cuenta_contable': re.compile(r"\b\d{6,9}\b"),  # Cuentas tipo 100000, 113000
            'subcuenta': re.compile(r"\b\d{3,4}000\b"),  # Subcuentas terminadas en 000
            'asiento': re.compile(r"\b\d{8,12}\b"),  # Números de asiento largos
            'referencia': re.compile(r"\b\d{2,4}[-/]\d{2,4}\b"),  # Referencias tipo 156-39
            
            # Importes y montos
            'importe_formal': re.compile(r"[-]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?"),  # 1.234.567,89
            'importe_negativo': re.compile(r"-\d+[.,]?\d*"),  # Importes negativos
            'importe_parentesis': re.compile(r"\(\d+[.,]?\d*\)"),  # Importes entre paréntesis
            
            # Fechas contables
            'fecha_iso': re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # 2024-01-01
            'fecha_euro': re.compile(r"\b\d{2}[/.-]\d{2}[/.-]\d{4}\b"),  # 31/12/2024
            'fecha_compacta': re.compile(r"\b\d{6}\b|\b\d{8}\b"),  # 311224 o 31122024
            'periodo': re.compile(r"\b(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b", re.IGNORECASE),
            'ejercicio': re.compile(r"\b(ejercicio\s+)?20\d{2}\b", re.IGNORECASE),
            
            # Códigos y referencias
            'codigo_doc': re.compile(r"\b[A-Z]{2,4}[-]?\d{4,10}\b"),  # RT, SA, etc.
            'numero_linea': re.compile(r"^\s*\d{3}\s"),  # 001, 002, 003 al inicio
            'id_documento': re.compile(r"\b\d{10,12}\b"),  # IDs largos de documento
            
            # Moneda
            'moneda': re.compile(r"\b(EUR|USD|GBP|€|\$|£)\b", re.IGNORECASE),
            
            # Balances
            'saldo_cero': re.compile(r"\b0[.,]00?\b"),  # 0.00 o 0,00
            'cuadre': re.compile(r"^\s*0+\s*$"),  # Líneas con solo ceros
        }
    
    def _init_keywords(self):
        """Keywords específicos de libros diarios contables"""
        self.keywords = {
            # Headers típicos
            'header_strong': {
                'cuenta', 'asiento', 'fecha', 'documento', 'referencia',
                'debe', 'haber', 'saldo', 'importe', 'descripción',
                'texto', 'denominación', 'concepto', 'glosa'
            },
            
            # Headers secundarios
            'header_weak': {
                'nº', 'núm', 'número', 'id', 'cód', 'código',
                'fec', 'doc', 'ref', 'cta', 'mov', 'tipo'
            },
            
            # Metadata del reporte
            'meta': {
                'libro diario', 'libro mayor', 'diario general',
                'empresa', 'sociedad', 'ejercicio', 'período',
                'página', 'pág', 'hoja', 'fecha emisión',
                'hora', 'usuario', 'cif', 'nif', 'ruc'
            },
            
            # Totales y sumas
            'total': {
                'total', 'totales', 'suma', 'sumas', 'subtotal',
                'acumulado', 'arrastre', 'saldo', 'resultado',
                'suma y sigue', 'van', 'vienen'
            },
            
            # Operaciones contables
            'operacion': {
                'apertura', 'cierre', 'ajuste', 'regularización',
                'provisión', 'amortización', 'reclasificación',
                'traspaso', 'transferencia', 'contabilización'
            },
            
            # Parent (asientos principales)
            'parent': {
                'asiento', 'comprobante', 'póliza', 'partida',
                'registro', 'operación', 'transacción', 'movimiento'
            },
            
            # Child (líneas de detalle) - específicas de asientos
            'child': {
                'detalle', 'línea', 'posición', 'item', 'partida',
                'apunte', 'imputación', 'subcuenta', 
                'falta nº cta', 'línea asiento', 'detalle asiento'
            }
        }
    
    # ===========================
    # FEATURES ESTRUCTURALES
    # ===========================
    
    def extract_structural_features(self, text: str) -> Dict[str, float]:
        """Features estructurales básicas del texto"""
        if not self.config.enable_structural:
            return {}
            
        features = {}
        
        # Longitud y espacios
        features['length'] = len(text)
        features['indent'] = len(text) - len(text.lstrip())
        features['trailing_spaces'] = len(text) - len(text.rstrip())
        
        # Estructura de datos tabulares (sin pipes/tabs)
        # Detectamos columnas por múltiples espacios consecutivos
        multi_spaces = re.findall(r'\s{3,}', text)
        features['column_gaps'] = len(multi_spaces)
        features['has_columns'] = int(len(multi_spaces) >= 2)
        
        # Separadores y líneas especiales
        features['is_separator'] = int(bool(self.patterns['separator'].search(text)))
        features['is_empty'] = int(len(text.strip()) == 0)
        features['is_numeric_only'] = int(text.strip().replace('.', '').replace(',', '').replace('-', '').replace(' ', '').isdigit() if text.strip() else False)
        
        # Alineación de texto
        stripped = text.strip()
        if stripped and len(text) > len(stripped):
            # Detecta si está centrado
            left_spaces = len(text) - len(text.lstrip())
            right_spaces = len(text) - len(text.rstrip())
            features['is_centered'] = int(abs(left_spaces - right_spaces) < 3 and left_spaces > 5)
        else:
            features['is_centered'] = 0
        
        # Densidad de caracteres especiales
        if text:
            features['digit_ratio'] = sum(c.isdigit() for c in text) / len(text)
            features['letter_ratio'] = sum(c.isalpha() for c in text) / len(text)
            features['space_ratio'] = sum(c.isspace() for c in text) / len(text)
            
            # Ratio de mayúsculas (importante para headers)
            letters = [c for c in text if c.isalpha()]
            features['upper_ratio'] = sum(c.isupper() for c in letters) / max(1, len(letters))
        else:
            features['digit_ratio'] = 0
            features['letter_ratio'] = 0
            features['space_ratio'] = 0
            features['upper_ratio'] = 0
            
        return features
    
    # ===========================
    # FEATURES CONTABLES
    # ===========================
    
    def extract_accounting_features(self, text: str) -> Dict[str, float]:
        """Features específicas de contabilidad y libros diarios"""
        if not self.config.enable_accounting:
            return {}
            
        features = {}
        
        # Cuentas contables
        cuentas = self.patterns['cuenta_contable'].findall(text)
        features['cuenta_count'] = len(cuentas)
        features['has_cuenta'] = int(len(cuentas) > 0)
        features['has_subcuenta'] = int(bool(self.patterns['subcuenta'].search(text)))
        
        # Números de asiento y referencias
        features['has_asiento'] = int(bool(self.patterns['asiento'].search(text)))
        features['has_referencia'] = int(bool(self.patterns['referencia'].search(text)))
        features['has_id_documento'] = int(bool(self.patterns['id_documento'].search(text)))
        
        # Importes y montos
        importes = self.patterns['importe_formal'].findall(text)
        features['importe_count'] = len(importes)
        features['has_importe'] = int(len(importes) > 0)
        features['has_multiple_importes'] = int(len(importes) >= 2)  # Debe y Haber
        
        # Importes negativos o entre paréntesis (común en contabilidad)
        features['has_negativo'] = int(bool(self.patterns['importe_negativo'].search(text)))
        features['has_parentesis'] = int(bool(self.patterns['importe_parentesis'].search(text)))
        
        # Balance y cuadre
        features['has_saldo_cero'] = int(bool(self.patterns['saldo_cero'].search(text)))
        features['is_cuadre_line'] = int(bool(self.patterns['cuadre'].search(text)))
        
        # Fechas contables
        has_fecha = bool(
            self.patterns['fecha_iso'].search(text) or 
            self.patterns['fecha_euro'].search(text) or
            self.patterns['fecha_compacta'].search(text)
        )
        features['has_fecha'] = int(has_fecha)
        features['has_periodo'] = int(bool(self.patterns['periodo'].search(text)))
        features['has_ejercicio'] = int(bool(self.patterns['ejercicio'].search(text)))
        
        # Moneda
        features['has_moneda'] = int(bool(self.patterns['moneda'].search(text)))
        
        # Códigos de documento
        features['has_codigo_doc'] = int(bool(self.patterns['codigo_doc'].search(text)))
        
        # Para PARENT-CHILD: numeración de líneas
        if self.config.doc_type == DocumentType.PARENT_CHILD:
            features['has_numero_linea'] = int(bool(self.patterns['numero_linea'].match(text)))
        
        # Patrones de debe/haber
        text_lower = text.lower()
        features['has_debe_haber'] = int('debe' in text_lower or 'haber' in text_lower)
        features['has_cargo_abono'] = int('cargo' in text_lower or 'abono' in text_lower)
        
        # Detectar líneas de saldo o balance
        balance_indicators = ['saldo', 'balance', 'total', 'suma']
        features['is_balance_line'] = int(any(ind in text_lower for ind in balance_indicators) and len(importes) > 0)
        
        return features
    
    # ===========================
    # FEATURES DE KEYWORDS
    # ===========================
    
    def extract_keyword_features(self, text: str) -> Dict[str, float]:
        """Features basadas en keywords específicos"""
        if not self.config.enable_keywords:
            return {}
            
        features = {}
        text_lower = text.lower()
        
        # Headers
        features['header_strong_kw'] = sum(1 for kw in self.keywords['header_strong'] if kw in text_lower)
        features['header_weak_kw'] = sum(1 for kw in self.keywords['header_weak'] if kw in text_lower)
        features['is_header_candidate'] = int(
            features['header_strong_kw'] >= 2 or 
            (features['header_strong_kw'] >= 1 and features['header_weak_kw'] >= 1)
        )
        
        # Metadata
        features['meta_kw'] = sum(1 for kw in self.keywords['meta'] if kw in text_lower)
        features['is_meta'] = int(features['meta_kw'] >= 2)
        
        # Totales
        features['total_kw'] = sum(1 for kw in self.keywords['total'] if kw in text_lower)
        features['is_total'] = int(features['total_kw'] > 0)
        
        # Operaciones contables
        features['operacion_kw'] = sum(1 for kw in self.keywords['operacion'] if kw in text_lower)
        features['has_operacion'] = int(features['operacion_kw'] > 0)
        
        # Para PARENT-CHILD
        if self.config.doc_type == DocumentType.PARENT_CHILD:
            features['parent_kw'] = sum(1 for kw in self.keywords['parent'] if kw in text_lower)
            features['child_kw'] = sum(1 for kw in self.keywords['child'] if kw in text_lower)
            features['is_parent_candidate'] = int(features['parent_kw'] > 0)
            features['is_child_candidate'] = int(features['child_kw'] > 0)
        
        return features
    
    # ===========================
    # FEATURES DE PATRONES
    # ===========================
    
    def extract_pattern_features(self, text: str) -> Dict[str, float]:
        """Features basadas en patrones específicos del documento"""
        if not self.config.enable_pattern:
            return {}
            
        features = {}
        
        # Patrones de encabezado de página
        page_patterns = [
            r'pág\.?\s*\d+',  # Pág. 1
            r'página\s*\d+',  # Página 1
            r'hoja\s*\d+',    # Hoja 1
            r'page\s*\d+',    # Page 1
        ]
        features['has_page_number'] = int(any(re.search(p, text, re.IGNORECASE) for p in page_patterns))
        
        # Patrones de continuación
        continuation_patterns = [
            r'suma y sigue',
            r'van\s+[\d.,]+',
            r'vienen\s+[\d.,]+',
            r'arrastre',
            r'carry\s*forward',
        ]
        features['has_continuation'] = int(any(re.search(p, text, re.IGNORECASE) for p in continuation_patterns))
        
        # Líneas con asteriscos (común en totales)
        features['has_asterisks'] = int('**' in text or '***' in text)
        
        # Patrón de línea de detalle típica (número + texto + importes)
        detail_pattern = r'^\s*\d+\s+.+\s+[\d.,]+\s+[\d.,]+\s*$'
        features['is_detail_pattern'] = int(bool(re.match(detail_pattern, text)))
        
        # Detectar líneas con estructura cuenta-descripción
        account_desc_pattern = r'^\s*\d{6,9}\s+[A-Za-záéíóúñÁÉÍÓÚÑ\s]+\s*'
        features['has_account_description'] = int(bool(re.match(account_desc_pattern, text)))
        
        # Para HEADER-DATA: detectar estructura columnar consistente
        if self.config.doc_type == DocumentType.HEADER_DATA:
            # Verificar si tiene al menos 2 grupos de espacios grandes (columnas)
            parts = re.split(r'\s{3,}', text.strip())
            features['column_count'] = len(parts)
            features['has_columnar_structure'] = int(len(parts) >= 3)
        
        # Para PARENT-CHILD: detectar jerarquía por indentación
        else:
            indent = len(text) - len(text.lstrip())
            features['indent_level'] = indent // 4  # Asumiendo 4 espacios por nivel
            features['is_indented'] = int(indent > 0)
        
        return features
    
    # ===========================
    # FEATURES CONTEXTUALES
    # ===========================
    
    def extract_contextual_features(self, texts: List[str], index: int) -> Dict[str, float]:
        """Features que dependen del contexto (líneas anteriores/siguientes)"""
        if not self.config.enable_contextual:
            return {}
            
        features = {}
        n = len(texts)
        
        # Posición en el documento
        features['relative_position'] = index / max(1, n - 1)
        features['is_first_10'] = int(index < 10)
        features['is_last_10'] = int(index >= n - 10)
        
        # Contexto inmediato
        prev_text = texts[index - 1] if index > 0 else ""
        next_text = texts[index + 1] if index < n - 1 else ""
        current_text = texts[index]
        
        # Análisis de línea anterior
        if prev_text:
            features['prev_is_separator'] = int(bool(self.patterns['separator'].search(prev_text)))
            features['prev_is_empty'] = int(len(prev_text.strip()) == 0)
            features['prev_has_total'] = int(any(kw in prev_text.lower() for kw in self.keywords['total']))
            
            # Para importes
            prev_importes = self.patterns['importe_formal'].findall(prev_text)
            features['prev_has_importes'] = int(len(prev_importes) > 0)
            
            # Continuidad de cuentas
            prev_cuenta = self.patterns['cuenta_contable'].search(prev_text)
            curr_cuenta = self.patterns['cuenta_contable'].search(current_text)
            if prev_cuenta and curr_cuenta:
                features['cuenta_sequence'] = int(prev_cuenta.group()[:3] == curr_cuenta.group()[:3])
            else:
                features['cuenta_sequence'] = 0
        
        # Análisis de línea siguiente
        if next_text:
            features['next_is_separator'] = int(bool(self.patterns['separator'].search(next_text)))
            features['next_is_empty'] = int(len(next_text.strip()) == 0)
            features['next_has_importes'] = int(bool(self.patterns['importe_formal'].search(next_text)))
        
        # Patrones de agrupación
        features['between_separators'] = int(
            features.get('prev_is_separator', 0) == 1 and 
            features.get('next_is_separator', 0) == 1
        )
        
        # Para PARENT-CHILD: cambios de indentación
        if self.config.doc_type == DocumentType.PARENT_CHILD:
            curr_indent = len(current_text) - len(current_text.lstrip())
            if prev_text:
                prev_indent = len(prev_text) - len(prev_text.lstrip())
                features['indent_increase'] = int(curr_indent > prev_indent)
                features['indent_decrease'] = int(curr_indent < prev_indent)
                features['same_indent'] = int(curr_indent == prev_indent)
            
            if next_text:
                next_indent = len(next_text) - len(next_text.lstrip())
                features['next_indent_increase'] = int(next_indent > curr_indent)
        
        # Detectar bloques de datos contables
        # Un bloque típicamente empieza después de un header y termina en un total
        if index > 0 and index < n - 1:
            # Verificar si estamos en un bloque de datos
            is_in_data_block = (
                not features.get('prev_is_separator', 0) and
                not features.get('next_is_separator', 0) and
                (features.get('prev_has_importes', 0) or features.get('next_has_importes', 0))
            )
            features['in_data_block'] = int(is_in_data_block)
        
        return features
    
    # ===========================
    # PIPELINE PRINCIPAL
    # ===========================
    
    def extract_features(self, text: str, texts: List[str], index: int) -> Dict[str, float]:
        """Extrae todas las features configuradas para una línea"""
        features = {}
        
        # Features por categoría
        features.update(self.extract_structural_features(text))
        features.update(self.extract_accounting_features(text))
        features.update(self.extract_keyword_features(text))
        features.update(self.extract_pattern_features(text))
        features.update(self.extract_contextual_features(texts, index))
        
        return features
    
    def extract_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrae features para todo el DataFrame"""
        df = df.copy()
        df['text'] = df['text'].fillna('').astype(str)
        texts = df['text'].tolist()
        
        all_features = []
        for i, text in enumerate(texts):
            features = self.extract_features(text, texts, i)
            all_features.append(features)
        
        return pd.DataFrame(all_features)
