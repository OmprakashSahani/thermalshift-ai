"""Tests for the deterministic modeled site registry."""

from zoneinfo import ZoneInfo

from thermalshift.domain.sites import get_default_sites


def test_default_sites_are_exactly_four_in_stable_order() -> None:
    expected_ids = ["ashburn-va", "phoenix-az", "san-antonio-tx", "atlanta-ga"]

    assert [site.site_id for site in get_default_sites()] == expected_ids
    assert [site.site_id for site in get_default_sites()] == expected_ids


def test_default_site_ids_are_unique() -> None:
    site_ids = [site.site_id for site in get_default_sites()]

    assert len(site_ids) == len(set(site_ids))


def test_default_site_coordinates_match_modeled_us_locations() -> None:
    coordinates = [(site.latitude, site.longitude) for site in get_default_sites()]

    assert coordinates == [
        (39.0437, -77.4875),
        (33.4484, -112.0740),
        (29.4241, -98.4936),
        (33.7490, -84.3880),
    ]


def test_default_sites_have_valid_timezones() -> None:
    assert all(ZoneInfo(site.timezone) for site in get_default_sites())


def test_default_site_capacities_are_synthetic_64_gpu_parameters() -> None:
    assert all(site.total_gpu_capacity == 64 for site in get_default_sites())
    assert all("Modeled" in site.name for site in get_default_sites())


def test_default_sites_return_new_immutable_values() -> None:
    first = get_default_sites()
    second = get_default_sites()

    assert first == second
    assert first is not second
    assert all(left is not right for left, right in zip(first, second, strict=True))
