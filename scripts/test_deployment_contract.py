import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_XCCONFIG = "COUNSELOR_API_BASE_URL = https:/$()/counselor-agent-web.onrender.com/"


class DeploymentContractTest(unittest.TestCase):
    def test_render_blueprint_declares_only_the_web_product(self):
        blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertEqual(blueprint.count("  - type: web"), 1)
        self.assertIn("name: counselor-agent-web", blueprint)
        self.assertIn(
            "startCommand: python scripts/web_workbench.py --host 0.0.0.0 --port $PORT",
            blueprint,
        )

    def test_ios_build_variants_use_the_web_product_host(self):
        for relative in ("ios-app/Config/Debug.xcconfig", "ios-app/Config/Release.xcconfig"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(EXPECTED_XCCONFIG, content)

    def test_environment_example_keeps_required_product_configuration(self):
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        for name in (
            "DEEPSEEK_API_KEY=",
            "DEEPSEEK_BASE_URL=",
            "DEEPSEEK_MODEL=",
            "WORKBENCH_USER=",
            "WORKBENCH_PASSWORD=",
        ):
            self.assertIn(name, example)


if __name__ == "__main__":
    unittest.main()
