from site_health_audit.cli import normalize, read_inputs, flat
from site_health_audit import audit

def test_normalize():
    assert normalize("example.com") == "https://example.com/"
    assert normalize("http://a.io/x?y") == "http://a.io/"
    assert normalize("https://www.google.com/maps/place/x") is None
    assert normalize("") is None

def test_csv_dedupe(tmp_path):
    p = tmp_path / "l.csv"; p.write_text("name,website\nA,a.com\nB,https://a.com/\nC,\nD,yelp.com/biz/x\n")
    assert read_inputs([str(p)], None) == ["https://a.com/"]

def test_audit_flags_bare_page():
    r = audit("http://x.com/", 200, "<html><body>hi</body></html>", {}, 100)
    assert r["needsWebsiteHelp"] is True and r["healthScore"] < 50

def test_flat():
    assert flat({"tech": [{"name": "Wix"}, {"name": "GA4"}]})["tech"] == "Wix;GA4"
