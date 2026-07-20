from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceMaterialKind = Literal["strategy", "service", "playbook", "knowledge_card", "policy", "index"]
SourceMaterialImportStatus = Literal["import_pending", "excerpt_review_required", "imported"]


class ContentSourceMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    file_name: str
    title: str
    kind: SourceMaterialKind
    word_count: int = Field(ge=0)
    digest_prefix: str = Field(min_length=8, max_length=16)
    privacy_class: Literal["redacted_only"] = "redacted_only"
    import_status: SourceMaterialImportStatus = "import_pending"
    source_path: str


_MATERIALS: tuple[ContentSourceMaterial, ...] = (
    ContentSourceMaterial(
        source_id="ekologus_material_strategy",
        file_name="01_STRATEGIA_BIZNESOWA_EKOLOGUS.cleaned.md",
        title="Strategia biznesowa Ekologus",
        kind="strategy",
        word_count=356,
        digest_prefix="e27259ca8b5b3fc3",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/01_STRATEGIA_BIZNESOWA_EKOLOGUS.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_portfolio",
        file_name="02_PORTFEL_USLUG_I_MODELE_PRZYCHODU.cleaned.md",
        title="Portfel usług i modele przychodu",
        kind="service",
        word_count=321,
        digest_prefix="3bbbfbdae02ca38f",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/02_PORTFEL_USLUG_I_MODELE_PRZYCHODU.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_eko_opieka",
        file_name="03_EKO_OPIEKA_I_EKO_KALENDARZ_PLAYBOOK.cleaned.md",
        title="Eko-Opieka i Eko Kalendarz",
        kind="playbook",
        word_count=255,
        digest_prefix="b3ed8d97a9f5262b",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/03_EKO_OPIEKA_I_EKO_KALENDARZ_PLAYBOOK.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_sales_followup",
        file_name="04_SPRZEDAZ_MARKETING_FOLLOWUP.cleaned.md",
        title="Sprzedaż, marketing i follow-up",
        kind="playbook",
        word_count=211,
        digest_prefix="de3b411e4d96d550",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/04_SPRZEDAZ_MARKETING_FOLLOWUP.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb001",
        file_name="KB_001_EKO_OPIEKA.cleaned.md",
        title="Eko-Opieka",
        kind="knowledge_card",
        word_count=166,
        digest_prefix="4493485707a7d57b",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/KB_001_EKO_OPIEKA.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb002",
        file_name="KB_002_PLATNE_KONSULTACJE.cleaned.md",
        title="Płatne konsultacje",
        kind="knowledge_card",
        word_count=170,
        digest_prefix="6fa8f44f428cb4ac",
        import_status="imported",
        source_path="materials_clean/approved/KB_002_PLATNE_KONSULTACJE.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb003",
        file_name="KB_003_AUDYT_ZGODNOSCI.cleaned.md",
        title="Audyt zgodności",
        kind="knowledge_card",
        word_count=191,
        digest_prefix="21b71a2eadeeee3c",
        import_status="imported",
        source_path="materials_clean/approved/KB_003_AUDYT_ZGODNOSCI.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb006",
        file_name="KB_006_KWALIFIKACJA_LEADA.cleaned.md",
        title="Kwalifikacja leada",
        kind="knowledge_card",
        word_count=177,
        digest_prefix="e7fdcf5c70b0cf8a",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/KB_006_KWALIFIKACJA_LEADA.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb008",
        file_name="KB_008_WYCENA_I_STAWKI.cleaned.md",
        title="Wycena i stawki",
        kind="knowledge_card",
        word_count=155,
        digest_prefix="e958790e0cd9445e",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/KB_008_WYCENA_I_STAWKI.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb013",
        file_name="KB_013_REGULY_ZRODEL_I_STATUSOW.cleaned.md",
        title="Reguły źródeł i statusów",
        kind="policy",
        word_count=137,
        digest_prefix="504e467f4a874230",
        import_status="imported",
        source_path="materials_clean/approved/KB_013_REGULY_ZRODEL_I_STATUSOW.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb014",
        file_name="KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md",
        title="Styl marki i język Ekologus",
        kind="policy",
        word_count=306,
        digest_prefix="8186c09a4f715e64",
        import_status="imported",
        source_path="materials_clean/approved/KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb015",
        file_name="KB_015_GENERATOR_TRESCI.cleaned.md",
        title="Generator treści",
        kind="policy",
        word_count=147,
        digest_prefix="f4f6fbb12eb19fa2",
        import_status="imported",
        source_path="materials_clean/approved/KB_015_GENERATOR_TRESCI.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb021",
        file_name="KB_021_BEZPIECZENSTWO_PRAWNE_POUFNOSC_ZGODY.cleaned.md",
        title="Bezpieczeństwo prawne, poufność i zgody",
        kind="policy",
        word_count=146,
        digest_prefix="536c173c0e2b074b",
        import_status="imported",
        source_path="materials_clean/approved/KB_021_BEZPIECZENSTWO_PRAWNE_POUFNOSC_ZGODY.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_kb022",
        file_name="KB_022_HISTORIA_I_AUTORYTET.cleaned.md",
        title="Historia, autorytet i ekspertyza",
        kind="knowledge_card",
        word_count=143,
        digest_prefix="d953adb33bb7d1b4",
        import_status="imported",
        source_path="materials_clean/approved/KB_022_HISTORIA_I_AUTORYTET.cleaned.md",
    ),
    ContentSourceMaterial(
        source_id="ekologus_material_index",
        file_name="KB_INDEX.cleaned.md",
        title="Indeks korpusu Ekologusa",
        kind="index",
        word_count=302,
        digest_prefix="c933b0e08b057e29",
        import_status="excerpt_review_required",
        source_path="materials_clean/approved/KB_INDEX.cleaned.md",
    ),
)


@lru_cache(maxsize=1)
def ekologus_source_materials() -> tuple[ContentSourceMaterial, ...]:
    return _MATERIALS
