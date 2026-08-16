"""Comprehensive logical tests for CodeGraph Studio Web UI.

Tests cover:
  1. HTML DOM integrity — all JS-referenced IDs exist, tab targets resolve
  2. CSS class consistency — all HTML classes have CSS definitions
  3. Tab switching logic — data-tab attributes match tab-content IDs
  4. Graph data integrity — edge endpoints reference valid nodes
  5. ARIA accessibility — roles, labels, aria-selected correctness
  6. API endpoint integration — all backend routes return valid responses
  7. Static asset pipeline — CSS/JS/HTML serve correctly with headers
  8. SEO and meta tags — title, description, favicon present
  9. Diff viewer structure — deletions/additions properly marked
  10. Cross-file contract — JS element selectors exist in HTML
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from fastapi.testclient import TestClient
from codegraph.api.app import app


# ═══════════════════════════════════════════════════════════
# Helper: lightweight HTML parser to extract DOM structure
# ═══════════════════════════════════════════════════════════

class DOMInspector(HTMLParser):
    """Parse HTML and extract element IDs, classes, data attributes, and tags."""

    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.classes: set[str] = set()
        self.data_tabs: list[str] = []  # data-tab values on tab-buttons
        self.tag_attrs: list[tuple[str, dict]] = []
        self.aria_roles: list[str] = []
        self.aria_labels: list[str] = []
        self.meta_tags: list[dict] = []
        self.title_text: str = ""
        self._in_title = False
        self.link_rels: list[dict] = []
        self.script_srcs: list[str] = []
        self.input_ids: list[str] = []
        self.button_ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tag_attrs.append((tag, attr_dict))

        if "id" in attr_dict:
            self.ids.add(attr_dict["id"])
        if "class" in attr_dict:
            for cls in attr_dict["class"].split():
                self.classes.add(cls)
        if "data-tab" in attr_dict:
            self.data_tabs.append(attr_dict["data-tab"])
        if "role" in attr_dict:
            self.aria_roles.append(attr_dict["role"])
        if "aria-label" in attr_dict:
            self.aria_labels.append(attr_dict["aria-label"])
        if tag == "meta":
            self.meta_tags.append(attr_dict)
        if tag == "link":
            self.link_rels.append(attr_dict)
        if tag == "script" and "src" in attr_dict:
            self.script_srcs.append(attr_dict["src"])
        if tag == "input" and "id" in attr_dict:
            self.input_ids.append(attr_dict["id"])
        if tag == "button" and "id" in attr_dict:
            self.button_ids.append(attr_dict["id"])
        if tag == "title":
            self._in_title = True

    def handle_data(self, data):
        if self._in_title:
            self.title_text += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def _get_dom() -> DOMInspector:
    """Fetch index.html and parse into DOMInspector."""
    client = TestClient(app)
    html = client.get("/").text
    dom = DOMInspector()
    dom.feed(html)
    return dom


def _get_css() -> str:
    client = TestClient(app)
    return client.get("/static/css/studio.css").text


def _get_js() -> str:
    client = TestClient(app)
    return client.get("/static/js/app.js").text


# ═══════════════════════════════════════════════════════════
# 1. HTML DOM Integrity
# ═══════════════════════════════════════════════════════════

class TestDOMIntegrity:
    """Every element ID referenced in JS must exist in HTML."""

    def test_js_getelementbyid_targets_exist_in_html(self) -> None:
        """All document.getElementById('x') calls in JS must have matching ids in HTML,
        unless the JS creates the element dynamically (create-if-missing pattern)."""
        dom = _get_dom()
        js = _get_js()

        # Extract all getElementById calls
        js_ids = set(re.findall(r"getElementById\(['\"](\w[\w-]*?)['\"]\)", js))
        assert len(js_ids) > 0, "JS must reference at least one element by ID"

        # IDs that JS creates dynamically if missing (create-if-missing pattern)
        # e.g. showToast() creates the toast div on first call
        dynamically_created = set()
        for eid in js_ids:
            # Check for pattern: getElementById('x') ... createElement ... id = 'x'
            if re.search(rf"getElementById\(['\"]{ eid }['\"]\).*?createElement", js, re.DOTALL):
                dynamically_created.add(eid)

        missing = js_ids - dom.ids - dynamically_created
        assert missing == set(), f"JS references IDs not in HTML: {missing}"

    def test_tab_data_attributes_resolve_to_tab_content_ids(self) -> None:
        """Every data-tab value on a tab-button must match an element ID in the DOM."""
        dom = _get_dom()
        assert len(dom.data_tabs) >= 3, "Must have at least 3 tab buttons"

        for tab_id in dom.data_tabs:
            assert tab_id in dom.ids, f"data-tab='{tab_id}' has no matching element id"

    def test_exactly_one_active_tab_content_on_load(self) -> None:
        """Exactly one tab-content should have 'active' class on initial load."""
        client = TestClient(app)
        html = client.get("/").text
        # Count elements with both tab-content and active classes
        active_tabs = re.findall(r'class="tab-content active"', html)
        assert len(active_tabs) == 1, f"Expected 1 active tab-content, found {len(active_tabs)}"

    def test_exactly_one_active_tab_button_on_load(self) -> None:
        """Exactly one tab-button should have 'active' class on initial load."""
        client = TestClient(app)
        html = client.get("/").text
        active_buttons = re.findall(r'class="tab-button active"', html)
        assert len(active_buttons) == 1, f"Expected 1 active tab-button, found {len(active_buttons)}"

    def test_active_tab_button_matches_active_content(self) -> None:
        """The active tab-button's data-tab must equal the active tab-content's id."""
        client = TestClient(app)
        html = client.get("/").text
        btn_match = re.search(r'class="tab-button active" data-tab="(\w[\w-]*)"', html)
        content_match = re.search(r'id="(\w[\w-]*)" class="tab-content active"', html)
        assert btn_match and content_match, "Must have both active tab-button and tab-content"
        assert btn_match.group(1) == content_match.group(1), (
            f"Active tab mismatch: button targets '{btn_match.group(1)}' "
            f"but active content is '{content_match.group(1)}'"
        )

    def test_unique_element_ids(self) -> None:
        """No duplicate IDs in the HTML document."""
        client = TestClient(app)
        html = client.get("/").text
        all_ids = re.findall(r'id="([\w-]+)"', html)
        duplicates = [x for x in all_ids if all_ids.count(x) > 1]
        assert len(set(duplicates)) == 0, f"Duplicate element IDs: {set(duplicates)}"


# ═══════════════════════════════════════════════════════════
# 2. CSS Class Consistency
# ═══════════════════════════════════════════════════════════

class TestCSSConsistency:
    """CSS classes used in HTML should have corresponding CSS rules."""

    def test_critical_css_classes_have_rules(self) -> None:
        """Core structural classes used in HTML must exist as CSS selectors."""
        css = _get_css()
        critical_classes = [
            "top-header", "brand", "brand-badge", "brand-title",
            "sidebar", "nav-item", "workspace", "graph-panel",
            "inspector-panel", "tab-button", "tab-content",
            "card", "step-card", "evidence-badge", "diff-container",
            "diff-add", "diff-del", "btn", "btn-primary", "btn-ghost",
            "data-table", "badge-match", "badge-conflict",
            "status-bar", "toast",
        ]
        for cls in critical_classes:
            assert f".{cls}" in css, f"CSS rule for .{cls} is missing"

    def test_css_design_tokens_are_defined(self) -> None:
        """All custom properties referenced in CSS must be defined in :root."""
        css = _get_css()
        # Extract all var(--xxx) references
        used_vars = set(re.findall(r"var\(--([\w-]+)\)", css))
        # Extract all --xxx: definitions in :root
        defined_vars = set(re.findall(r"--([\w-]+)\s*:", css))

        undefined = used_vars - defined_vars
        assert undefined == set(), f"CSS vars used but not defined in :root: {undefined}"

    def test_no_invalid_css_properties(self) -> None:
        """Check for known invalid CSS properties."""
        css = _get_css()
        # 'shrink' is not valid; must be 'flex-shrink'
        lines = css.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("shrink:"):
                assert False, f"Line {i}: Invalid property 'shrink:' — use 'flex-shrink:'"


# ═══════════════════════════════════════════════════════════
# 3. Graph Data Integrity
# ═══════════════════════════════════════════════════════════

class TestGraphDataIntegrity:
    """The graph canvas must render live API data, not hardcoded demo nodes."""

    def test_graph_fetched_from_real_endpoint(self) -> None:
        """JS must fetch graph data from /repositories/{id}/graph — no demo literals."""
        js = _get_js()
        assert "/repositories/" in js and "/graph" in js, "JS must load the graph from the API"
        assert "renderGraph(svg, nodes, edges)" in js, "JS must render fetched nodes/edges"
        # No hardcoded demo node/edge arrays may remain
        assert not re.search(r"id:\s*'(UserService|AuthService|PostgreSQL|Redis|ArchDiagram)'", js), (
            "Hardcoded demo graph nodes found in JS"
        )

    def test_graph_endpoint_returns_nodes_and_edges(self) -> None:
        """/repositories/{id}/graph returns the documented node/edge structure."""
        client = TestClient(app)
        r = client.get("/repositories/repo:test/graph")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "nodes" in data and "edges" in data
        # Without Neo4j configured the endpoint reports the reason honestly
        if not data["nodes"]:
            assert "note" in data

    def test_graph_stats_badge_is_live(self) -> None:
        """The node/edge count badge is populated at runtime, not hardcoded."""
        dom = _get_dom()
        assert "graph-stats" in dom.ids, "graph-stats badge missing from HTML"
        html = TestClient(app).get("/").text
        assert "5 nodes" not in html, "Static node count must not be hardcoded"


# ═══════════════════════════════════════════════════════════
# 4. ARIA Accessibility
# ═══════════════════════════════════════════════════════════

class TestAccessibility:
    """ARIA roles and labels must be correct for assistive technology."""

    def test_tablist_role_exists(self) -> None:
        dom = _get_dom()
        assert "tablist" in dom.aria_roles, "Missing role='tablist' on tabs container"

    def test_tab_roles_exist(self) -> None:
        dom = _get_dom()
        tab_count = dom.aria_roles.count("tab")
        assert tab_count >= 3, f"Expected ≥3 role='tab' elements, found {tab_count}"

    def test_tabpanel_roles_exist(self) -> None:
        dom = _get_dom()
        panel_count = dom.aria_roles.count("tabpanel")
        assert panel_count >= 3, f"Expected ≥3 role='tabpanel' elements, found {panel_count}"

    def test_nav_has_aria_label(self) -> None:
        dom = _get_dom()
        assert "Main navigation" in dom.aria_labels, "Sidebar nav missing aria-label"

    def test_graph_section_has_aria_label(self) -> None:
        dom = _get_dom()
        labels = dom.aria_labels
        assert any("Knowledge Graph" in l or "Graph" in l for l in labels), (
            "Graph canvas section missing aria-label"
        )


# ═══════════════════════════════════════════════════════════
# 5. API Endpoint Integration
# ═══════════════════════════════════════════════════════════

class TestAPIEndpoints:
    """All REST API endpoints return correct status and structure."""

    def test_root_serves_html(self) -> None:
        client = TestClient(app)
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_health_returns_healthy(self) -> None:
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["data"]["status"] == "healthy"

    def test_health_includes_correlation_headers(self) -> None:
        client = TestClient(app)
        r = client.get("/health")
        assert "X-Request-ID" in r.headers, "Missing X-Request-ID header"
        assert "X-Trace-ID" in r.headers, "Missing X-Trace-ID header"
        assert r.headers["X-Request-ID"].startswith("req_")

    def test_repository_crud_lifecycle(self) -> None:
        """Register → List → Get → verify full lifecycle."""
        client = TestClient(app)

        # Register
        r = client.post("/repositories", json={"path": "/tmp/test-repo", "name": "test-repo"})
        assert r.status_code == 200
        reg_data = r.json()["data"]
        repo_id = reg_data["repository_id"]
        assert repo_id.startswith("repository:")

        # List
        r = client.get("/repositories")
        assert r.status_code == 200

        # Get by ID
        r = client.get(f"/repositories/{repo_id}")
        assert r.status_code == 200

    def test_path_traversal_rejected(self) -> None:
        client = TestClient(app)
        r = client.post("/repositories", json={"path": "../../etc/passwd", "name": "evil"})
        assert r.status_code == 400

    def test_query_endpoint(self) -> None:
        client = TestClient(app)
        r = client.post("/query", json={"query": "Where is UserService?", "repository_id": "repo:test"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert "trace_id" in data["data"]

    def test_investigate_endpoint(self) -> None:
        client = TestClient(app)
        r = client.post("/investigate", json={"question": "Why auth fails?", "repository_id": "repo:test"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert "investigation_id" in data["data"]

    def test_change_plan_endpoint(self) -> None:
        client = TestClient(app)
        r = client.post("/changes/plan", json={"change_request": "Refactor auth", "repository_id": "repo:test"})
        assert r.status_code == 200
        data = r.json()
        assert data["data"]["requires_approval"] is True

    def test_repair_endpoint(self) -> None:
        client = TestClient(app)
        # Reference a real sample-project symbol so the planner can ground the repair.
        r = client.post("/repairs", json={
            "failure_message": "UserService.add_user raised ValueError on None input",
            "repository_id": "repo:test",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["repair_status"] in {"REPAIRED", "FAILED", "ABORTED"}, (
            f"Unexpected repair status: {data['repair_status']}"
        )
        assert "iterations" in data and "final_patch" in data

    def test_evaluation_endpoint(self) -> None:
        client = TestClient(app)
        r = client.get("/evaluations/latest")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["benchmark_cases"] == 780
        assert data["quality_gate"] is True

    def test_multimodal_index_endpoint(self) -> None:
        client = TestClient(app)
        r = client.post("/repositories/repo:test/multimodal/index")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "INDEXED"

    def test_drift_endpoint(self) -> None:
        client = TestClient(app)
        r = client.get("/repositories/repo:test/drift")
        assert r.status_code == 200

    def test_openapi_docs_available(self) -> None:
        client = TestClient(app)
        r = client.get("/docs")
        assert r.status_code == 200
        r2 = client.get("/openapi.json")
        assert r2.status_code == 200
        schema = r2.json()
        assert schema["info"]["version"] == "16.0.0"


# ═══════════════════════════════════════════════════════════
# 6. SEO and Meta Tags
# ═══════════════════════════════════════════════════════════

class TestSEO:
    """HTML head must contain proper meta tags, title, and favicon."""

    def test_title_tag_present(self) -> None:
        dom = _get_dom()
        assert "CodeGraph Studio" in dom.title_text

    def test_meta_description_present(self) -> None:
        dom = _get_dom()
        desc_tags = [m for m in dom.meta_tags if m.get("name") == "description"]
        assert len(desc_tags) == 1, "Must have exactly one meta description"
        assert len(desc_tags[0].get("content", "")) > 20, "Meta description too short"

    def test_viewport_meta_present(self) -> None:
        dom = _get_dom()
        viewports = [m for m in dom.meta_tags if m.get("name") == "viewport"]
        assert len(viewports) == 1

    def test_favicon_present(self) -> None:
        dom = _get_dom()
        icons = [l for l in dom.link_rels if l.get("rel") == "icon"]
        assert len(icons) >= 1, "Must have a favicon link"

    def test_charset_declared(self) -> None:
        dom = _get_dom()
        charsets = [m for m in dom.meta_tags if "charset" in m]
        assert len(charsets) >= 1
        assert charsets[0]["charset"].upper() == "UTF-8"


# ═══════════════════════════════════════════════════════════
# 7. Diff Viewer Structure
# ═══════════════════════════════════════════════════════════

class TestDiffViewer:
    """Diff viewer must render real patches from the API with correct coloring."""

    def test_diff_container_present_with_empty_state(self) -> None:
        dom = _get_dom()
        assert "diff-viewer" in dom.ids, "diff-viewer container missing from HTML"
        html = TestClient(app).get("/").text
        assert "No patch generated yet" in html, "Diff viewer must start in an explicit empty state"

    def test_render_diff_classifies_lines(self) -> None:
        """renderDiff() must classify header/range/add/del lines of a unified diff."""
        js = _get_js()
        for marker in ("diff-header", "diff-range", "diff-add", "diff-del"):
            assert marker in js, f"renderDiff must apply .{marker}"

    def test_diff_classes_have_css_styling(self) -> None:
        css = _get_css()
        assert ".diff-add" in css
        assert ".diff-del" in css
        assert ".diff-header" in css
        assert ".diff-range" in css


# ═══════════════════════════════════════════════════════════
# 8. JS-HTML Contract
# ═══════════════════════════════════════════════════════════

class TestJSHTMLContract:
    """JavaScript querySelector selectors must match HTML elements."""

    def test_js_queryselectorall_classes_exist_in_html(self) -> None:
        """All querySelectorAll('.class') selectors in JS must have matching HTML classes."""
        js = _get_js()
        dom = _get_dom()

        # Extract class selectors from querySelectorAll
        selectors = re.findall(r"querySelectorAll\(['\"]\.(\w[\w-]*)['\"]", js)
        for sel in selectors:
            assert sel in dom.classes, f"JS selects '.{sel}' but class not in HTML"

    def test_js_does_not_use_alert(self) -> None:
        """JS must use toast notifications, not native alert()."""
        js = _get_js()
        # Remove comments before checking
        js_no_comments = re.sub(r"//.*$", "", js, flags=re.MULTILINE)
        assert "alert(" not in js_no_comments, "JS uses alert() instead of showToast()"

    def test_js_event_handlers_target_existing_elements(self) -> None:
        """Button IDs referenced in initActions() must exist in HTML."""
        dom = _get_dom()
        assert "btn-approve" in dom.ids, "btn-approve missing from HTML"
        assert "btn-run-query" in dom.ids, "btn-run-query missing from HTML"
        assert "search-input" in dom.ids, "search-input missing from HTML"
        assert "inspect-header" in dom.ids, "inspect-header missing from HTML"
        assert "graph-svg" in dom.ids, "graph-svg missing from HTML"

    def test_svg_arrow_marker_defined(self) -> None:
        """JS references url(#arrow) — marker must be defined in HTML SVG."""
        html = TestClient(app).get("/").text
        dom = _get_dom()
        assert "arrow" in dom.ids, "SVG marker id='arrow' missing"


# ═══════════════════════════════════════════════════════════
# 9. Status Bar & Navigation
# ═══════════════════════════════════════════════════════════

class TestStatusBar:
    """Footer status bar must display correct system state."""

    def test_status_bar_present(self) -> None:
        dom = _get_dom()
        assert "status-bar" in dom.classes

    def test_status_bar_shows_version(self) -> None:
        html = TestClient(app).get("/").text
        assert "v16.0" in html

    def test_status_bar_shows_eval_cases_element(self) -> None:
        """Eval case count is a live element populated from /evaluations/latest."""
        dom = _get_dom()
        assert "stat-eval-cases" in dom.ids, "stat-eval-cases element missing from footer"

    def test_eval_case_count_matches_real_dataset(self) -> None:
        """The endpoint must report the actual number of evaluation dataset cases."""
        client = TestClient(app)
        data = client.get("/evaluations/latest").json()["data"]
        dataset = json.loads(Path("tests/evaluation/eval_dataset_full.json").read_text())
        assert data["benchmark_cases"] == len(dataset)

    def test_status_bar_shows_repo_count_element(self) -> None:
        dom = _get_dom()
        assert "stat-repos" in dom.ids, "stat-repos element missing from footer"


class TestSidebarNavigation:
    """Sidebar must have correct navigation items."""

    def test_all_nav_sections_present(self) -> None:
        html = TestClient(app).get("/").text
        assert "Knowledge Graph" in html
        assert "Investigation Console" in html
        assert "Change Planner" in html
        assert "Architecture Drift" in html
        assert "Git" in html
        assert "Observability" in html

    def test_exactly_one_active_nav_item(self) -> None:
        html = TestClient(app).get("/").text
        active_navs = re.findall(r'class="nav-item active"', html)
        assert len(active_navs) == 1, f"Expected 1 active nav-item, found {len(active_navs)}"
