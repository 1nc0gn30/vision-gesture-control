"""
vision-gesture-control: Zero-dependency MCP Server, CLI & UI Server for Vision Gesture Control.
"""

__version__ = "1.0.0"
__author__ = "Google DeepMind Advanced Agentic Coding"
__license__ = "MIT"

from .mcp_server import (
    MCPServer,
    classify_gesture,
    calculate_dwell,
    classify_face,
    generate_action_map,
    get_diagnostics,
    generate_mcp_client_config,
    MCP_TOOLS_DEFINITIONS,
)
from .ui_server import UIServer, create_ui_server, run_ui_server
from .cli import main as cli_main

# Optional re-exports from sibling core modules
try:
    from .gestures import (
        Point3D,
        GestureType,
        HandGestureClassifier,
        DwellDetector,
        FaceGestureClassifier,
        ActionBinding,
        ActionBindingSchema,
        ActionDispatcher,
    )
except ImportError:
    pass

try:
    from .trajectory import (
        TrajectoryPoint,
        TrajectoryStroke,
        TrajectoryTracker,
        calculate_pinch_zoom_delta,
    )
except ImportError:
    pass

try:
    from .filter_pipeline import (
        OneEuroFilter,
        OneEuroFilter3D,
        MovingAverageFilter,
        LandmarkSmoother,
        FilterPipeline,
    )
except ImportError:
    pass

try:
    from .compat import (
        PlatformDiagnostics,
        DisplayServer,
        CameraDiscovery,
        AudioFeedback,
        KeySimulator,
    )
except ImportError:
    pass

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "MCPServer",
    "UIServer",
    "create_ui_server",
    "run_ui_server",
    "classify_gesture",
    "calculate_dwell",
    "classify_face",
    "generate_action_map",
    "get_diagnostics",
    "generate_mcp_client_config",
    "MCP_TOOLS_DEFINITIONS",
    "cli_main",
    "TrajectoryPoint",
    "TrajectoryStroke",
    "TrajectoryTracker",
    "calculate_pinch_zoom_delta",
]
