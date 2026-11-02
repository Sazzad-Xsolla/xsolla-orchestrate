#!/usr/bin/env python3
"""Build the single-file Xsolla run template from supplied design-system assets."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build():
    import base64
    assets = ROOT / "assets"
    base = (assets / "xui/base.html").read_text()
    logo = (assets / "xui/logo.svg").read_text()
    styles = (assets / "xui/button.css").read_text() + "\n" + (assets / "field-team.css").read_text() + "\n" + (assets / "rpg.css").read_text() + "\n" + (assets / "cozy.css").read_text()
    scene = "data:image/png;base64," + base64.b64encode((assets / "field-team/field-station.png").read_bytes()).decode()
    styles += "\n" + (assets / "cozy-world.css").read_text().replace("__SCENE__", scene)
    content = (assets / "field-team.html").read_text().replace("__LOGO__", logo).replace("__SCENE__", scene)
    sheet = "data:image/png;base64," + base64.b64encode((assets / "field-team/cozy-world.png").read_bytes()).decode()
    portrait = "data:image/png;base64," + base64.b64encode((assets / "field-team/atlas-portrait.png").read_bytes()).decode()
    script = (assets / "motion-state.js").read_text() + "\n" + (assets / "field-team.js").read_text().replace("__CHARACTERS__", sheet).replace("__ATLAS_PORTRAIT__", portrait)
    html = base.replace("{{PAGE_TITLE}}", "__TITLE__ · Xsolla Field Team").replace("{{COMPONENT_STYLES}}", styles).replace("{{PAGE_CONTENT}}", content + "\n<script>\n" + script + "\n</script>")
    output = ROOT / "prototypes/xsolla-run.html"
    output.parent.mkdir(exist_ok=True)
    output.write_text(html)
    return output


if __name__ == "__main__":
    print(build())
