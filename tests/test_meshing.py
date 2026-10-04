import zipfile
import xml.etree.ElementTree as ET

import pytest

from rav4shelf import fileio, layout, meshing, params

from conftest import make


def test_coupon_mesh_is_watertight_and_positive(p, d):
    m = meshing.coupon_mesh(p, d)
    assert meshing.check_closed(m) == []
    assert m.signed_volume() > 0


def test_coupon_mesh_dimensions_car_frame(p, d):
    m = meshing.coupon_mesh(p, d)
    (x0, y0, z0), (x1, y1, z1) = m.bbox()
    assert z1 == pytest.approx(d.z_top)
    assert z0 == pytest.approx(d.z_top - d.coupon_rim_height)
    assert y0 == pytest.approx(d.y_front)
    assert y1 == pytest.approx(d.y_rear)
    # widest point: top of the band (walls lean outward), just behind the rounded front
    # corners (the cubby narrows toward the rear)
    y = d.y_front + p.corner_radius_front
    widest = params.cubby_width(p, y, d.z_top) - 2 * p.side_gap
    assert x1 - x0 == pytest.approx(widest, abs=0.05)


def test_coupon_volume_matches_profile_area(p, d):
    """Volume ~= profile cross-section area x outline perimeter (thin band)."""
    m = meshing.coupon_mesh(p, d)
    t, h = p.coupon_plate_thickness, d.coupon_rim_height
    w_r, w_f = p.coupon_rim_width, p.coupon_flange_width
    section = w_r * h + (w_f - w_r) * t
    ring = layout.shelf_outline(p, d, d.z_top, w_f / 2).ring(8)
    perim = sum(((ring[i][0] - ring[i - 1][0]) ** 2 + (ring[i][1] - ring[i - 1][1]) ** 2) ** 0.5
                for i in range(len(ring)))
    assert m.signed_volume() == pytest.approx(section * perim, rel=0.08)


def test_print_orientation(p, d):
    m = meshing.to_print_orientation(meshing.coupon_mesh(p, d))
    (x0, y0, z0), (x1, y1, z1) = m.bbox()
    assert z0 == pytest.approx(0.0)
    assert z1 == pytest.approx(d.coupon_rim_height)
    assert (x0 + x1) == pytest.approx(0.0) and (y0 + y1) == pytest.approx(0.0)
    assert meshing.check_closed(m) == []
    # the plate (full flange width) is on the bed: many vertices at z = 0
    assert m.signed_volume() > 0


@pytest.mark.parametrize("over", [
    {},
    {"port_notch_width": 0.0},
    {"wall_lean_deg": -3.0, "wall_radius": 0.0},  # walls lean inward
    {"W_rear_delta": -12.0, "rear_corner_length": 0.0, "rear_corner_r_back": 0.0},
    {"rear_corner_length": 40.0, "rear_corner_inset": 12.0, "rear_corner_r_side": 20.0},
    {"corner_radius_front": 0.0, "port_notch_radius": 0.0},
    {"coupon_flange_width": 20.0, "coupon_rim_height": 30.0},
    {"X_ports": -40.0, "port_notch_width": 50.0},
])
def test_coupon_variants_stay_watertight(over):
    p, d = make(**over)
    m = meshing.coupon_mesh(p, d)
    assert meshing.check_closed(m) == []


def test_trimesh_agrees_if_available(p, d):
    trimesh = pytest.importorskip("trimesh")
    np = pytest.importorskip("numpy")
    m = meshing.to_print_orientation(meshing.coupon_mesh(p, d))
    t = trimesh.Trimesh(np.array(m.vertices), np.array(m.faces), process=False)
    assert t.is_watertight and t.is_winding_consistent and t.is_volume
    assert t.volume == pytest.approx(m.signed_volume())


def test_check_closed_detects_holes(p, d):
    m = meshing.coupon_mesh(p, d)
    broken = meshing.Mesh(m.vertices, m.faces[:-1])
    assert meshing.check_closed(broken)


def test_stl_roundtrip(tmp_path, p, d):
    m = meshing.to_print_orientation(meshing.coupon_mesh(p, d))
    path = tmp_path / "c.stl"
    fileio.write_stl(str(path), m.vertices, m.faces, "test")
    tris = fileio.read_stl(str(path))
    assert len(tris) == len(m.faces)
    assert path.stat().st_size == 84 + 50 * len(m.faces)


def test_3mf_is_valid_zip_with_model(tmp_path, p, d):
    m = meshing.to_print_orientation(meshing.coupon_mesh(p, d))
    path = tmp_path / "c.3mf"
    fileio.write_3mf(str(path), m.vertices, m.faces, "fit_coupon")
    with zipfile.ZipFile(str(path)) as z:
        assert set(z.namelist()) >= {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    assert root.get("unit") == "millimeter"
    assert len(root.findall(".//m:vertex", ns)) == len(m.vertices)
    assert len(root.findall(".//m:triangle", ns)) == len(m.faces)


def test_weld_merges_duplicates():
    verts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1.00000001, 0, 0), (0, 0, 0)]
    faces = [(0, 1, 2), (4, 3, 2), (0, 0, 1)]
    v2, f2 = fileio.weld(verts, faces)
    assert len(v2) == 3
    assert f2 == [(0, 1, 2), (0, 1, 2)]


def test_profile_gauge_is_watertight_and_sized(p, d):
    m = meshing.profile_gauge_mesh(p, d)
    assert meshing.check_closed(m) == []
    (x0, y0, z0), (x1, y1, z1) = m.bbox()
    assert z1 - z0 == pytest.approx(p.gauge_thickness)
    # widest just below the chamfered top corners
    full = params.cubby_width(p, p.gauge_y, p.H_cubby)
    below = params.cubby_width(p, p.gauge_y, p.H_cubby - p.gauge_corner) - 2 * p.gauge_clearance
    assert below - 0.1 <= x1 - x0 <= full
    height = params.roof_height(p, 0.0, p.gauge_y) - 2 * p.gauge_clearance
    assert y1 - y0 == pytest.approx(height, abs=0.1)


@pytest.mark.parametrize("over", [
    {"gauge_band": 3.0, "gauge_corner": 0.0},
    {"gauge_band": 10.0, "gauge_clearance": 0.0, "gauge_y": 60.0},
    {"gauge_corner": 2.0},             # raised to the minimum automatically
    {"roof_pocket_width": 0.0},
    {"wall_radius": 0.0, "wall_lean_deg": -2.0},
])
def test_profile_gauge_variants(over):
    from conftest import make
    p, d = make(**over)
    assert meshing.check_closed(meshing.profile_gauge_mesh(p, d)) == []


def test_envelope_mesh_is_watertight_and_follows_the_model(p, d):
    m = meshing.envelope_mesh(p, d)
    assert meshing.check_closed(m) == []
    (x0, y0, z0), (x1, y1, z1) = m.bbox()
    assert (y0, z0) == (pytest.approx(0.0), pytest.approx(0.0))
    assert (y1, z1) == (pytest.approx(p.D_cubby), pytest.approx(p.H_cubby))
    assert x0 == pytest.approx(-x1)
    widest = max(params.cubby_half_width(p, 0.0, z) for z in layout.envelope_levels(p))
    assert x1 == pytest.approx(widest, abs=0.01)


@pytest.mark.parametrize("over", [{"wall_radius": 0.0}, {"W_rear_delta": 0.0},
                                  {"rear_corner_r_side": 0.0, "rear_corner_r_back": 0.0}])
def test_envelope_mesh_variants(over):
    p, d = make(**over)
    assert meshing.check_closed(meshing.envelope_mesh(p, d)) == []
