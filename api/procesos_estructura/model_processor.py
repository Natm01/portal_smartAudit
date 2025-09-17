# procesos_estructura/model_processor.py
import os
import re
import json
import pickle
import numpy as np
import pandas as pd
import csv
from typing import Optional, List, Dict, Any

try:
    import xgboost as xgb  # noqa: F401
except Exception:
    pass

class LoadedModel:
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.model = None
        self.label_encoder = None
        self.feature_names: Optional[List[str]] = None
        self.model_info: Dict[str, Any] = {}

    def load(self):
        model_file = os.path.join(self.model_dir, "model.pkl")
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"No se encontró el modelo en {model_file}")
        with open(model_file, "rb") as f:
            self.model = pickle.load(f)

        encoder_file = os.path.join(self.model_dir, "label_encoder.pkl")
        if not os.path.exists(encoder_file):
            raise FileNotFoundError(f"No se encontró el label encoder en {encoder_file}")
        with open(encoder_file, "rb") as f:
            self.label_encoder = pickle.load(f)

        features_file = os.path.join(self.model_dir, "feature_names.txt")
        if not os.path.exists(features_file):
            raise FileNotFoundError(f"No se encontró feature_names.txt en {features_file}")
        with open(features_file, "r", encoding="utf-8") as f:
            self.feature_names = [line.strip() for line in f if line.strip()]

        info_file = os.path.join(self.model_dir, "model_info.json")
        if os.path.exists(info_file):
            with open(info_file, "r", encoding="utf-8") as f:
                self.model_info = json.load(f)
        else:
            self.model_info = {
                "model_type": type(self.model).__name__,
                "num_features": len(self.feature_names),
                "classes": list(map(str, getattr(self.label_encoder, "classes_", []))),
            }

class DocumentPredict:
    def __init__(self, model_dirs: List[str]):
        if not model_dirs:
            raise ValueError("Debes proporcionar al menos un directorio de modelo.")
        self.models: List[LoadedModel] = []
        for md in model_dirs:
            lm = LoadedModel(md)
            lm.load()
            self.models.append(lm)

        self._last_is_txt = False
        self._fallback_thr = 0.7
        self._header_confidence_threshold = 0.7

    def _read_text_file(self, file_path: str, encoding: str = "utf-8") -> pd.DataFrame:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()
        base = os.path.basename(file_path)
        return pd.DataFrame({
            "file": base,
            "line_no": np.arange(1, len(lines) + 1),
            "text": [line.rstrip("\r\n") for line in lines],
            "label": "UNKNOWN",
        })

    def _sniff_encoding(self, file_path: str) -> Optional[str]:
        with open(file_path, "rb") as fb:
            head = fb.read(4)
        if head.startswith(b"\xff\xfe"):
            return "utf-16le"
        if head.startswith(b"\xfe\xff"):
            return "utf-16be"
        if head.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        return None

    def _read_csv_or_excel(self, file_path: str) -> pd.DataFrame:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".xlsx"]:
            df = pd.read_excel(file_path, dtype=str, header=None,).fillna("")
            texts = (df.astype(str).agg(" | ".join, axis=1)).tolist() if df.shape[1] > 1 else df.iloc[:, 0].astype(str).tolist()
            base = os.path.basename(file_path)
            return pd.DataFrame({"file": base, "line_no": np.arange(1, len(texts)+1), "text": texts, "label": "UNKNOWN"})

        sniff = self._sniff_encoding(file_path)
        enc_candidates = ([sniff] if sniff else []) + ["utf-16", "utf-8", "latin-1", "cp1252"]
        sep_candidates = [None, ",", ";", "\t", "|"]

        last_err = None
        for enc in enc_candidates:
            for sep in sep_candidates:
                try:
                    df = pd.read_csv(file_path, dtype=str, sep=sep, encoding=enc, engine="python").fillna("")
                    df = df.replace({r"\t": " | ", r"\\t": " | "}, regex=True)
                    
                    texts = (
                        df.apply(lambda row: " | ".join([c.strip() for c in row]), axis=1)
                        .str.replace(r"\s*\|\s*", " | ", regex=True)
                        .tolist()
                    )
                    base = os.path.basename(file_path)
                    return pd.DataFrame({"file": base, "line_no": np.arange(1, len(texts)+1), "text": texts, "label": "UNKNOWN"})
                except Exception as e:
                    last_err = e
        raise last_err

    def load_test_file(self, file_path: str, encoding: str = "utf-8") -> pd.DataFrame:
        print(f"Cargando archivo de test: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".txt"]:
            self._last_is_txt = True
            return self._read_text_file(file_path, encoding=encoding)
        elif ext in [".csv", ".xlsx", ".xls"]:
            self._last_is_txt = False
            return self._read_csv_or_excel(file_path)
        else:
            self._last_is_txt = True
            return self._read_text_file(file_path, encoding=encoding)

    @staticmethod
    def _align_features(features_df: pd.DataFrame, expected_names: List[str]) -> pd.DataFrame:
        missing = [c for c in expected_names if c not in features_df.columns]
        for c in missing:
            features_df[c] = 0
        extra = [c for c in features_df.columns if c not in expected_names]
        if extra:
            features_df = features_df.drop(columns=extra)
        features_df = features_df[expected_names]
        for col in features_df.columns:
            if features_df[col].dtype == "object":
                features_df[col] = pd.to_numeric(features_df[col], errors="coerce").fillna(0)
        return features_df.fillna(0)

    @staticmethod
    def _guess_roles(model_dirs: List[str]) -> Dict[str, str]:
        """Returns dict {role: model_dir} based on folder name heuristics"""
        role_map: Dict[str, str] = {}
        lowers = [(md, os.path.basename(md).lower()) for md in model_dirs]
        
        for md, name in lowers:
            if "parent" in name:
                role_map["parent"] = md
            if "header" in name or "data_header" in name or "dataheader" in name or "header_data" in name:
                role_map["header"] = md
        
        if "parent" not in role_map:
            role_map["parent"] = model_dirs[0]
        if "header" not in role_map:
            role_map["header"] = model_dirs[-1] if len(model_dirs) > 1 else model_dirs[0]
        return role_map

    def _run_model_with_header_fallback(self, lm: LoadedModel, base_features: pd.DataFrame) -> pd.DataFrame:
        """Execute model with fallback for low confidence HEADER predictions"""
        from procesos_estructura.feature_processor import DocumentFeatureExtractor
        
        # Extract features if not provided
        if base_features.empty:
            feature_extractor = DocumentFeatureExtractor()
            # This would need the actual dataframe, simplified for cleanup
            base_features = pd.DataFrame()
        
        feats = self._align_features(base_features.copy(), lm.feature_names)
        preds = lm.model.predict(feats)
        if preds.dtype not in (np.int64, np.int32):
            preds = preds.astype(int)
        
        if hasattr(lm.model, "predict_proba"):
            probas = lm.model.predict_proba(feats)
        else:
            probas = np.zeros((len(preds), len(lm.label_encoder.classes_)))
            for i, p in enumerate(preds):
                probas[i, p] = 1.0

        final_labels = []
        final_confidences = []
        
        for i, (pred_idx, row_probas) in enumerate(zip(preds, probas)):
            original_label = lm.label_encoder.inverse_transform([pred_idx])[0]
            original_confidence = row_probas[pred_idx]
            
            if original_label == "HEADER" and original_confidence < self._header_confidence_threshold:
                sorted_indices = np.argsort(row_probas)[::-1]
                
                fallback_found = False
                for idx in sorted_indices:
                    candidate_label = lm.label_encoder.inverse_transform([idx])[0]
                    candidate_confidence = row_probas[idx]
                    
                    if candidate_label != "HEADER" and candidate_confidence > 0.1:
                        final_labels.append(candidate_label)
                        final_confidences.append(candidate_confidence)
                        fallback_found = True
                        print(f"HEADER fallback: línea {i+1} - {original_label}({original_confidence:.3f}) -> {candidate_label}({candidate_confidence:.3f})")
                        break
                
                if not fallback_found:
                    final_labels.append(original_label)
                    final_confidences.append(original_confidence)
            else:
                final_labels.append(original_label)
                final_confidences.append(original_confidence)

        dfm = pd.DataFrame({
            "predicted_label": final_labels,
            "confidence": final_confidences,
        })
        
        for i, class_name in enumerate(lm.label_encoder.classes_):
            dfm[f"prob@{os.path.basename(lm.model_dir)}::{class_name}"] = probas[:, i]
        
        return dfm

    def predict_file(self, test_df: pd.DataFrame) -> pd.DataFrame:
        print("Extrayendo features del archivo de test...")
        
        # Import here to avoid circular imports
        from procesos_estructura.feature_processor import DocumentFeatureExtractor
        
        tmp_df = test_df.copy()
        if not self._last_is_txt:
            tmp_df["text"] = tmp_df["text"].str.replace("|", " ", regex=False)

        feature_extractor = DocumentFeatureExtractor()
        base_features = feature_extractor.extract_all_features(tmp_df).reset_index(drop=True)

        role_map = self._guess_roles([lm.model_dir for lm in self.models])
        parent_dir = role_map["parent"]
        header_dir = role_map["header"]

        lm_parent = next((lm for lm in self.models if lm.model_dir == parent_dir), self.models[0])
        lm_header = next((lm for lm in self.models if lm.model_dir == header_dir), self.models[-1])

        df_parent = self._run_model_with_header_fallback(lm_parent, base_features)
        mean_parent = float(df_parent["confidence"].mean())
        print(f"- {os.path.basename(parent_dir)} (PARENT-CHILD) -> mean={mean_parent:.3f}")

        chosen_dfm = df_parent
        chosen_dir = parent_dir
        chosen_role = "PARENT-CHILD"

        if (mean_parent < self._fallback_thr) and (header_dir != parent_dir):
            df_header = self._run_model_with_header_fallback(lm_header, base_features)
            mean_header = float(df_header["confidence"].mean())
            print(f"Umbral de fallback: {self._fallback_thr:.2f}. Media PARENT-CHILD < umbral -> probando DATA-HEADER")
            print(f"- {os.path.basename(header_dir)} (DATA-HEADER) -> mean={mean_header:.3f}")
            chosen_dfm = df_header
            chosen_dir = header_dir
            chosen_role = "DATA-HEADER"

        print(f"Modelo usado para TODO el archivo: {os.path.basename(chosen_dir)} [{chosen_role}] (conf media={chosen_dfm['confidence'].mean():.3f})")

        results_df = test_df.copy().reset_index(drop=True)
        results_df["predicted_label"] = chosen_dfm["predicted_label"]
        results_df["confidence"] = chosen_dfm["confidence"]
        
        for c in chosen_dfm.columns:
            if c not in ["predicted_label", "confidence"]:
                results_df[c] = chosen_dfm[c].values

        return results_df

    def save_results(self, results_df, output_file: str = "resultados_prediccion.csv"):
        print(f"\nGuardando resultados en {output_file}...")
        out_dir = os.path.dirname(output_file) or "."
        os.makedirs(out_dir, exist_ok=True)
        quoting_kwargs = {"quoting": csv.QUOTE_ALL}
        simple_cols = ["file", "line_no", "text", "predicted_label", "confidence"]
        results_df[simple_cols].to_csv(output_file, index=False, encoding="utf-8", lineterminator="\n", **quoting_kwargs)
        print("Resultados guardados (simple).")
        detailed_file = output_file.replace(".csv", "_detailed.csv")
        results_df.to_csv(detailed_file, index=False, encoding="utf-8", lineterminator="\n", **quoting_kwargs)
        print(f"Resultados detallados guardados en {detailed_file}")