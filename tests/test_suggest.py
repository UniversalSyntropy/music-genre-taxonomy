import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import suggest as S  # noqa: E402

URL = "https://en.wikipedia.org/wiki/Acid_house"


def node(k, n=None):
    return {"key": k, "name": n or k.title()}


DOC = {
    "nodes": [node("house", "House"), node("acid-house", "Acid House"), node("techno"), node("rock"),
              node("deep-house"), node("caf", "Café: it's 'x'")],
    "links": [{"child": "acid-house", "parent": "house"}, {"child": "deep-house", "parent": "house"}],
}


def body(change="Add a parent", child="techno", parent="house", url=URL, note="_No response_", nl="\n", tick="x"):
    return nl.join(["### Change", "", change, "", "### Genre key", "", child, "", "### Parent key", "", parent, "",
                    "### Public source URL", "", url, "", "### Note", "", note, "", "### Licence", "",
                    f"- [{tick}] I agree that this suggestion is published under CC BY 4.0.", ""])


def test_licence_box_must_be_ticked():
    assert check(tick="X") == []
    assert any("Licence" in e for e in check(tick=" "))
    assert any("Licence" in e for e in S.validate(S.parse_issue(body().replace("### Licence", "### Other")),
                                                   DOC, S.empty_contrib()))


def test_url_trailing_newline_rejected():
    assert S.URL_RE.fullmatch(URL + "\n") is None


def check(**kw):
    return S.validate(S.parse_issue(body(**kw)), DOC, S.empty_contrib())


def test_parse_lf_crlf_noresponse():
    a = S.parse_issue(body())
    b = S.parse_issue(body(nl="\r\n"))
    assert a == b
    assert a["change"] == "Add a parent" and a["child"] == "techno" and a["parent"] == "house"
    assert a["url"] == URL and a["note"] == ""
    assert S.parse_issue("### Genre key  \n\n  techno  \n")["child"] == "techno"


def test_missing_sections_error_not_crash():
    errs = S.validate(S.parse_issue("hello"), DOC, S.empty_contrib())
    assert len(errs) >= 4


def test_valid_add_and_rules():
    assert check() == []
    assert check(change="Delete it")
    assert check(child="nope")
    assert check(parent="Bad Key")
    assert check(child="a" * 81)
    assert check(child="house", parent="house")
    assert check(url="http://example.com/x")
    assert check(url="https://example.com/" + "a" * 300)
    assert check(url="https://example .com")


def test_duplicate_and_cycle_refused():
    assert any("already in the data" in e for e in check(child="acid-house", parent="house"))
    assert any("cycle" in e for e in check(child="house", parent="acid-house"))
    c = S.apply(S.parse_issue(body()), DOC, S.empty_contrib(), 5)
    assert any("already suggested" in e for e in S.validate(S.parse_issue(body()), DOC, c))
    # cycle through a contributed edge
    c = S.apply(S.parse_issue(body(child="techno", parent="rock")), DOC, S.empty_contrib(), 6)
    assert any("cycle" in e for e in S.validate(S.parse_issue(body(child="rock", parent="techno")), DOC, c))


def test_remove_rules():
    assert check(change="Remove a parent", child="acid-house", parent="house") == []
    assert any("not in the data" in e for e in check(change="Remove a parent", child="techno", parent="house"))
    s = S.parse_issue(body(change="Remove a parent", child="acid-house", parent="house"))
    c = S.apply(s, DOC, S.empty_contrib(), 7)
    assert any("already suggested" in e for e in S.validate(s, DOC, c))


def test_idempotent_rerun_replaces_entry(tmp_path):
    data, ct = tmp_path / "d.json", tmp_path / "c.yaml"
    data.write_text(json.dumps(DOC))
    for child in ("techno", "rock"):
        bf = tmp_path / "b.md"
        bf.write_text(body(child=child))
        assert S.main(["--issue", "3", "--body-file", str(bf), "--data", str(data), "--contrib", str(ct)]) == 0
    got = yaml.safe_load(ct.read_text())
    assert [e["child"] for e in got["add_edges"]] == ["rock"]
    first = ct.read_bytes()
    assert S.main(["--issue", "3", "--body-file", str(bf), "--data", str(data), "--contrib", str(ct)]) == 0
    assert ct.read_bytes() == first


def test_check_only_does_not_write(tmp_path):
    data, ct, bf = tmp_path / "d.json", tmp_path / "c.yaml", tmp_path / "b.md"
    data.write_text(json.dumps(DOC))
    bf.write_text(body())
    assert S.main(["--issue", "1", "--body-file", str(bf), "--data", str(data), "--contrib", str(ct), "--check-only"]) == 0
    assert not ct.exists()


def test_deterministic_sorted_bytes():
    s1 = S.parse_issue(body(child="techno"))
    s2 = S.parse_issue(body(child="deep-house", parent="techno"))
    a = S.apply(s2, DOC, S.apply(s1, DOC, S.empty_contrib(), 1), 2)
    b = S.apply(s1, DOC, S.apply(s2, DOC, S.empty_contrib(), 2), 1)
    assert S.dump_contrib(a) == S.dump_contrib(b)
    t = S.dump_contrib(a)
    assert t.startswith(S.HEADER + "version: 1\n")
    assert '  - {child: deep-house, child_name: Deep-House, parent: techno, parent_name: Techno, source_url: "' + URL + '", issue: 2}' in t
    assert [e["child"] for e in a["add_edges"]] == ["deep-house", "techno"]


def test_yaml_round_trip_odd_names():
    d = copy.deepcopy(DOC)
    d["nodes"] += [node("a-b", "A: b, {c} #d"), node("zz", "Zéé ジャズ")]
    for k in ("caf", "a-b", "zz"):
        c = S.apply(S.parse_issue(body(child=k, parent="rock")), d, S.empty_contrib(), 1)
        back = yaml.safe_load(S.dump_contrib(c))
        assert back["add_edges"] == c["add_edges"]


HOSTILE = ['x"y', "x\ny", "x`y", "<script>alert(1)</script>", "a: b}"]


@pytest.mark.parametrize("raw", HOSTILE)
def test_hostile_input_rejected_and_not_echoed(raw):
    for kw in ({"url": "https://example.com/" + raw}, {"child": raw}, {"parent": raw}):
        errs = S.validate(S.parse_issue(body(**kw)), DOC, S.empty_contrib())
        assert errs
        text = S.comment_bad(errs)
        for frag in ('x"y', "<script>", "a: b}", "`y", "alert(1)"):
            assert frag not in text


def test_hostile_via_cli(tmp_path):
    data, bf, out = tmp_path / "d.json", tmp_path / "b.md", tmp_path / "o.md"
    data.write_text(json.dumps(DOC))
    bf.write_text(body(child="<script>a: b}</script>"))
    rc = S.main(["--issue", "9", "--body-file", str(bf), "--data", str(data), "--contrib", str(tmp_path / "c.yaml"),
                 "--comment-out", str(out)])
    assert rc == 1 and "<script>" not in out.read_text()


def test_internal_error_exit_2(tmp_path):
    assert S.main(["--issue", "1", "--data", str(tmp_path / "missing.json")]) == 2


def test_build_guard(tmp_path):
    repo, src = tmp_path / "repo", tmp_path / "src"
    (repo / "contrib").mkdir(parents=True)
    (src / "data").mkdir(parents=True)
    pub, cp = repo / "contrib" / "hand-links.yaml", src / "data" / "contrib.yaml"
    pub.write_text((ROOT / "contrib" / "hand-links.yaml").read_text())
    build.check_contrib_copy(src, repo)  # empty, no copy: ok
    cp.write_bytes(pub.read_bytes())
    build.check_contrib_copy(src, repo)  # empty, identical: ok
    cp.write_text("other\n")
    with pytest.raises(SystemExit) as e:
        build.check_contrib_copy(src, repo)  # empty, differing: error
    assert "cp contrib/hand-links.yaml" in str(e.value)
    cp.unlink()
    c = S.apply(S.parse_issue(body()), DOC, S.empty_contrib(), 1)
    pub.write_text(S.dump_contrib(c))
    with pytest.raises(SystemExit):
        build.check_contrib_copy(src, repo)  # entries, no copy
    cp.write_text("stale\n")
    with pytest.raises(SystemExit):
        build.check_contrib_copy(src, repo)  # entries, stale
    cp.write_bytes(pub.read_bytes())
    build.check_contrib_copy(src, repo)  # entries, identical


def test_real_data_smoke(tmp_path):
    doc = json.loads((ROOT / "data" / "taxonomy.json").read_text())
    linked = {(l["child"], l["parent"]) for l in doc["links"]}
    keys = [n["key"] for n in doc["nodes"]]
    up = {}
    for l in doc["links"]:
        up.setdefault(l["child"], []).append(l["parent"])
    pair = next((c, p) for c in keys[:50] for p in keys[:50]
                if c != p and (c, p) not in linked and not S._reaches(linked, p, c))
    data, bf = tmp_path / "d.json", tmp_path / "b.md"
    data.write_text(json.dumps(doc))
    bf.write_text(body(child=pair[0], parent=pair[1]))
    ct = tmp_path / "c.yaml"
    assert S.main(["--issue", "1", "--body-file", str(bf), "--data", str(data), "--contrib", str(ct), "--check-only"]) == 0
    # The file that suggest.py writes must pass check.py's contrib check.
    ct = tmp_path / "contrib" / "hand-links.yaml"
    ct.parent.mkdir()
    assert S.main(["--issue", "1", "--body-file", str(bf), "--data", str(data), "--contrib", str(ct)]) == 0
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_mod", ROOT / "tools" / "check.py")
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    C.ROOT = tmp_path
    assert C.check_contrib(doc) is not None
    assert C.errors == []
