import os
from pathlib import Path
from typing import Optional, AsyncGenerator
from dataclasses import dataclass
from build123d import Shape, Compound, import_step
from build123d.topology import ShapeList


@dataclass
class StepComponent:
    name: str
    shape: Shape
    volume: float
    face_count: int
    bounding_box: dict


@dataclass
class StepLoadResult:
    components: list[StepComponent]
    total_volume: float
    component_count: int
    memory_estimate_mb: float


class StepLoader:
    def __init__(self, memory_envelope_mb: int = 1024):
        self.memory_envelope_mb = memory_envelope_mb
        self.memory_envelope_bytes = memory_envelope_mb * 1024 * 1024

    def load_step_progressive(
        self,
        file_path: str,
        max_components: Optional[int] = None
    ) -> StepLoadResult:
        """Load STEP file and return component metadata without loading all geometry into memory."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"STEP file not found: {file_path}")

        # Import the full assembly first to get component structure
        # In a real implementation, this would use OCC's XDE to read component-by-component
        assembly = import_step(file_path)
        if assembly is None:
            raise ValueError("Failed to parse STEP file")

        components = []
        total_volume = 0.0

        if isinstance(assembly, Compound):
            children = list(assembly.children())
        else:
            children = [assembly]

        for i, child in enumerate(children):
            if max_components and i >= max_components:
                break

            try:
                volume = child.volume
                faces = list(child.faces())
                bbox = child.bounding_box()

                components.append(StepComponent(
                    name=getattr(child, "label", f"Component_{i}"),
                    shape=child,
                    volume=volume,
                    face_count=len(faces),
                    bounding_box=bbox.to_dict() if bbox else {}
                ))
                total_volume += volume
            except Exception:
                continue

        # Estimate memory: ~1KB per face + geometry data
        face_total = sum(c.face_count for c in components)
        memory_estimate_mb = (face_total * 1024) / (1024 * 1024) + len(components) * 0.5

        return StepLoadResult(
            components=components,
            total_volume=total_volume,
            component_count=len(components),
            memory_estimate_mb=memory_estimate_mb
        )

    def load_component(self, file_path: str, component_index: int) -> Optional[Shape]:
        """Load a specific component by index (for progressive loading)."""
        assembly = import_step(file_path)
        if assembly is None:
            return None

        if isinstance(assembly, Compound):
            children = list(assembly.children())
        else:
            children = [assembly]

        if 0 <= component_index < len(children):
            return children[component_index]
        return None

    def check_memory_envelope(self, estimated_mb: float) -> bool:
        return estimated_mb <= self.memory_envelope_mb

    def get_load_plan(self, result: StepLoadResult) -> dict:
        """Determine which components can be loaded within memory envelope."""
        loadable = []
        skipped = []
        current_mb = 0.0

        for comp in result.components:
            comp_mb = (comp.face_count * 1024) / (1024 * 1024) + 0.5
            if current_mb + comp_mb <= self.memory_envelope_mb:
                loadable.append(comp)
                current_mb += comp_mb
            else:
                skipped.append(comp)

        return {
            "loadable": loadable,
            "skipped": skipped,
            "estimated_memory_mb": current_mb,
            "envelope_mb": self.memory_envelope_mb
        }