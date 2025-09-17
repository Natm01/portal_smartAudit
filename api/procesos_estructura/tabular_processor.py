# procesos_estructura/tabular_processor.py
import pandas as pd
import re
from typing import List, Tuple

def extract_columns_from_section(section_text: str) -> Tuple[List[str], List[int]]:
    """
    Extrae nombres de columnas de una sección
    Retorna: (columnas_con_nombre, indices_validos)
    """
    if not section_text or section_text.strip() == '':
        return [], []
    
    # Limpiar comillas
    clean_text = section_text.strip().strip('"')
    
    # Dividir por |
    raw_columns = clean_text.split('|')
    
    # Limpiar y procesar cada columna
    columns = []
    valid_indices = []  # Índices de columnas que tienen nombre
    
    for i, col in enumerate(raw_columns):
        col = col.strip()
        
        if col and col != '.' and col != '':
            # Columna con nombre válido - limpiar pero mantener original
            clean_col = re.sub(r'[^\w\s\.\-]', '', col)
            clean_col = re.sub(r'\s+', '_', clean_col.strip())
            if clean_col:
                columns.append(clean_col)
                valid_indices.append(i)
    
    return columns, valid_indices

def extract_data_from_section(section_text: str, valid_indices: List[int]) -> List[str]:
    """
    Extrae datos de una sección solo para las columnas válidas
    """
    if not section_text or section_text.strip() == '':
        return [''] * len(valid_indices)
    
    # Limpiar comillas
    clean_text = section_text.strip().strip('"')
    
    # Dividir por |
    raw_data = clean_text.split('|')
    
    # Extraer solo los datos de las columnas válidas
    data = []
    for index in valid_indices:
        if index < len(raw_data):
            field = raw_data[index].strip()
            if field == '.' or field == '':
                data.append('')
            else:
                data.append(field)
        else:
            data.append('')
    
    return data

def clean_numeric_field(value):
    """
    Limpia un campo numérico
    """
    if pd.isna(value) or value == '':
        return None
    
    if not isinstance(value, str):
        return value
    
    # Limpiar formato europeo
    cleaned = value.strip()
    
    # Manejar negativos
    is_negative = cleaned.startswith('-')
    if is_negative:
        cleaned = cleaned[1:]
    
    # Convertir formato europeo a estándar
    if ',' in cleaned and '.' in cleaned:
        # Formato: 1.234.567,89
        parts = cleaned.rsplit(',', 1)
        integer_part = parts[0].replace('.', '')
        decimal_part = parts[1]
        cleaned = f"{integer_part}.{decimal_part}"
    elif ',' in cleaned:
        # Solo coma como decimal
        cleaned = cleaned.replace(',', '.')
    
    result = f"-{cleaned}" if is_negative else cleaned
    return result

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el DataFrame
    """
    # Reemplazar strings vacíos con NaN
    df = df.replace('', pd.NA)
    
    # Convertir columnas numéricas
    for col in df.columns:
        if any(word in col.lower() for word in ['debe', 'haber', 'moneda', 'importe']):
            df[col] = df[col].apply(clean_numeric_field)
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convertir fechas
    for col in df.columns:
        if any(word in col.lower() for word in ['fecha', 'registrado']):
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    
    return df

def process_csv_tabular(file_path: str, output_path: str = None) -> pd.DataFrame:
    """
    Procesa un CSV que puede tener:
    - UNA sección con datos separados por |
    - DOS secciones separadas por la PRIMERA coma, cada una con datos separados por |
    
    Args:
        file_path: Ruta del archivo de entrada
        output_path: Ruta del archivo de salida (opcional)
    
    Returns:
        DataFrame con todas las columnas combinadas
    """
    
    # Leer archivo línea por línea
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]
    
    if not lines:
        raise ValueError("El archivo está vacío")
    
    print(f"Procesando {len(lines)} líneas...")
    
    # Procesar primera línea para obtener headers
    first_line = lines[0]
    print(f"Primera línea: {first_line[:100]}...")
    
    # Verificar si hay dos secciones (buscar primera coma)
    comma_position = first_line.find(',')
    has_two_sections = comma_position != -1
    
    if has_two_sections:
        print("✓ Detectadas DOS secciones separadas por coma")
        section1_header = first_line[:comma_position].strip()
        section2_header = first_line[comma_position + 1:].strip()
        
        print(f"Sección 1 header: {section1_header[:50]}...")
        print(f"Sección 2 header: {section2_header[:50]}...")
        
        # Extraer nombres de columnas de cada sección
        headers1, valid_indices1 = extract_columns_from_section(section1_header)
        headers2, valid_indices2 = extract_columns_from_section(section2_header)
        
        # Combinar todos los headers
        all_headers = headers1 + headers2
        
        print(f"Headers extraídos:")
        print(f"  Sección 1 ({len(headers1)}): {headers1}")
        print(f"  Sección 2 ({len(headers2)}): {headers2}")
        print(f"  Total columnas válidas: {len(all_headers)}")
        
    else:
        print("✓ Detectada UNA sección (sin coma separadora)")
        single_header = first_line.strip()
        
        print(f"Header único: {single_header[:50]}...")
        
        # Extraer nombres de columnas de la única sección
        headers1, valid_indices1 = extract_columns_from_section(single_header)
        headers2, valid_indices2 = [], []  # No hay segunda sección
        
        all_headers = headers1
        
        print(f"Headers extraídos:")
        print(f"  Sección única ({len(headers1)}): {headers1}")
        print(f"  Total columnas válidas: {len(all_headers)}")
    
    # Procesar el resto de las líneas
    all_data = []
    
    for i, line in enumerate(lines[1:], start=2):
        try:
            if has_two_sections:
                # Procesar línea con dos secciones
                comma_pos = line.find(',')
                
                if comma_pos == -1:
                    # Si no hay coma en esta línea, toda va a sección 1
                    section1_data = line.strip()
                    section2_data = ""
                else:
                    section1_data = line[:comma_pos].strip()
                    section2_data = line[comma_pos + 1:].strip()
                
                # Extraer datos de cada sección
                data1 = extract_data_from_section(section1_data, valid_indices1)
                data2 = extract_data_from_section(section2_data, valid_indices2)
                
                # Combinar datos de ambas secciones
                row_data = data1 + data2
                
            else:
                # Procesar línea con una sola sección
                single_data = line.strip()
                row_data = extract_data_from_section(single_data, valid_indices1)
            
            all_data.append(row_data)
            
        except Exception as e:
            print(f"Error en línea {i}: {e}")
            # Crear fila vacía si hay error
            if has_two_sections:
                empty_data1 = [''] * len(headers1)
                empty_data2 = [''] * len(headers2)
                all_data.append(empty_data1 + empty_data2)
            else:
                empty_data = [''] * len(headers1)
                all_data.append(empty_data)
    
    # Crear DataFrame
    df = pd.DataFrame(all_data, columns=all_headers)
    
    print(f"\nDataFrame creado: {df.shape[0]} filas × {df.shape[1]} columnas")
    
    # Limpiar datos
    df = clean_dataframe(df)
    
    # Guardar si se especifica ruta
    if output_path:
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Archivo guardado: {output_path}")
    
    return df

