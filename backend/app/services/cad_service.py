import os
import uuid
from pathlib import Path
from typing import Optional, BinaryIO
from build123d import Compound, import_step, export_step
from build123d.topology import Shape


class CadService:
    def __init__(self, upload_dir: str = "./data/uploads", max_size_mb: int = 500):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def save_upload(self, file: BinaryIO, filename: str) -> tuple[str, int]:
        file_id = uuid.uuid4().hex[:12]
        ext = Path(filename).suffix.lower()
        if ext not in [".step", ".stp"]:
            ext = ".step"
        save_path = self.upload_dir / f"{file_id}{ext}"

        size = 0
        chunk_size = 8192
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            size += len(chunk)
            if size > self.max_size_bytes:
                save_path.unlink(missing_ok=True)
                raise ValueError(f"File exceeds maximum size of {self.max_size_mb} MB")
            with open(save_path, "ab") as f:
                f.write(chunk)

        return str(save_path), size

    def load_solid(self, file_path: str) -> Shape:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"STEP file not found: {file_path}")
        solid = import_step(file_path)
        if solid is None:
            raise ValueError("Failed to parse STEP file - no solid geometry found")
        return solid

    def get_solid_info(self, solid: Shape) -> dict:
        try:
            volume = solid.volume
        except Exception:
            volume = 0.0

        faces = list(solid.faces())
        face_types = {}
        for face in faces:
            geom_type = face.geometry_type()
            face_types[geom_type] = face_types.get(geom_type, 0) + 1

        return {
            "volume": volume,
            "face_count": len(faces),
            "face_types": face_types,
            "bounding_box": solid.bounding_box().to_dict() if hasattr(solid, "bounding_box") else None
        }

    def validate_sheet_metal(self, solid: Shape) -> tuple[float, list[dict]]:
        """
        Validate constant-thickness sheet metal and detect bends.
        Returns (thickness, bends) where bends is a list of bend info dicts.
        Raises ValueError if not valid sheet metal.
        """
        faces = list(solid.faces())
        planar_faces = [f for f in faces if f.geometry_type() == "PLANE"]
        cylindrical_faces = [f for f in faces if f.geometry_type() == "CYLINDER"]

        if len(planar_faces) < 2:
            raise ValueError("Not enough planar faces for sheet metal")

        # Thickness detection via parallel face pairs with opposite normals
        thickness_votes = []
        for i, f1 in enumerate(planar_faces):
            for f2 in planar_faces[i+1:]:
                if self._are_parallel_opposite(f1, f2):
                    dist = self._face_distance(f1, f2)
                    if dist > 0:
                        thickness_votes.append(dist)

        if not thickness_votes:
            raise ValueError("No parallel face pairs found - not a sheet metal part")

        # Find consensus thickness
        thickness = self._consensus_thickness(thickness_votes)
        if thickness is None:
            raise ValueError("No single thickness consensus - variable thickness not supported")

        # Bend detection: coaxial cylindrical pairs with radius diff = thickness
        bends = []
        for i, c1 in enumerate(cylindrical_faces):
            for c2 in cylindrical_faces[i+1:]:
                bend = self._analyze_bend_pair(c1, c2, thickness)
                if bend:
                    bends.append(bend)

        if not bends:
            raise ValueError("No valid bends detected")

        return thickness, bends

    def _are_parallel_opposite(self, f1, f2) -> bool:
        try:
            n1 = f1.normal_at()
            n2 = f2.normal_at()
            dot = n1.dot(n2)
            return dot < -0.999  # Opposite normals
        except Exception:
            return False

    def _face_distance(self, f1, f2) -> float:
        try:
            c1 = f1.center()
            c2 = f2.center()
            n1 = f1.normal_at()
            return abs((c2 - c1).dot(n1))
        except Exception:
            return 0.0

    def _consensus_thickness(self, votes: list[float], tolerance: float = 0.01) -> Optional[float]:
        if not votes:
            return None
        votes.sort()
        # Find largest cluster within tolerance
        best_cluster = []
        current_cluster = [votes[0]]
        for v in votes[1:]:
            if abs(v - current_cluster[-1]) <= tolerance:
                current_cluster.append(v)
            else:
                if len(current_cluster) > len(best_cluster):
                    best_cluster = current_cluster
                current_cluster = [v]
        if len(current_cluster) > len(best_cluster):
            best_cluster = current_cluster
        if len(best_cluster) < 2:
            return None
        return sum(best_cluster) / len(best_cluster)

    def _analyze_bend_pair(self, c1, c2, thickness: float, tolerance: float = 0.01) -> Optional[dict]:
        try:
            # Check coaxial
            axis1 = c1.axis()
            axis2 = c2.axis()
            if not self._coaxial(axis1, axis2, tolerance):
                return None

            r1 = c1.radius
            r2 = c2.radius
            if abs(abs(r1 - r2) - thickness) > tolerance:
                return None

            # Inside radius is the smaller one
            r_in = min(r1, r2)
            # Angle from parametric sweep
            angle = self._bend_angle(c1, c2)
            if angle <= 0 or angle > 180:
                return None

            # Direction: which side material folds to
            direction = self._bend_direction(c1, c2)

            return {
                "inside_radius": r_in,
                "angle_degrees": angle,
                "axis": axis1,
                "direction": direction,
                "face_inner": c1 if r1 < r2 else c2,
                "face_outer": c2 if r1 < r2 else c1
            }
        except Exception:
            return None

    def _coaxial(self, axis1, axis2, tolerance: float) -> bool:
        # Same direction and position
        try:
            dir1 = axis1.direction
            dir2 = axis2.direction
            if abs(dir1.dot(dir2)) < 0.999:
                return False
            # Distance between axes
            p1 = axis1.position
            p2 = axis2.position
            v = p2 - p1
            dist = (v - v.project(dir1)).length
            return dist < tolerance
        except Exception:
            return False

    def _bend_angle(self, c1, c2) -> float:
        # Simplified - would need proper parametric range analysis
        return 90.0

    def _bend_direction(self, c1, c2) -> str:
        # Simplified - would need proper material side analysis
        return "up"