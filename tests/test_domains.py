from mailmap.domains import canonical_service_for_domain, meaningful_domain, registrable_domain


def test_registrable_domain_reduces_subdomain() -> None:
    assert registrable_domain("mail.github.com") == "github.com"


def test_meaningful_domain_preserves_alias_domain() -> None:
    assert meaningful_domain("accounts.google.com") == "google.com"


def test_canonical_service_aliases_google_family() -> None:
    assert canonical_service_for_domain("googlemail.com") == "Google"


def test_canonical_service_maps_brand_wrappers_to_main_service() -> None:
    assert canonical_service_for_domain("edm.br.sheinemail.com") == "SHEIN"
    assert canonical_service_for_domain("news.pokemongolive.com") == "Pokemon GO"


def test_canonical_service_ignores_public_suffix_only_domains() -> None:
    assert canonical_service_for_domain("com.br") is None


def test_canonical_service_maps_additional_clean_aliases() -> None:
    assert canonical_service_for_domain("wbgames.com") == "WB Games"
    assert canonical_service_for_domain("runwayml.com") == "Runway"
