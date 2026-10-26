from bot.core.i18n import uz, ru, en

LANG_MODULES = {
    "uz": uz,
    "ru": ru,
    "en": en,
}


def get_i18n(lang: str = "uz"):
    """Berilgan til kodi bo'yicha tegishli modulni qaytaradi (standart: uz)."""
    return LANG_MODULES.get(lang, uz)


def get_text(attr_name: str, lang: str = "uz", default: str = "") -> str:
    """Moduldan xavfsiz matn olish."""
    mod = get_i18n(lang)
    return getattr(mod, attr_name, getattr(uz, attr_name, default))


def get_button_variants(attr_name: str) -> list:
    """Tugmaning 3 ta tildagi barcha variantlarini ro'yxat sifatida qaytaradi."""
    variants = []
    for mod in [uz, ru, en]:
        val = getattr(mod, attr_name, None)
        if val and val not in variants:
            variants.append(val)
    return variants


def is_btn(text: str, attr_name: str) -> bool:
    """Xabar matni berilgan tugma nomining istalgan tiliga mos kelishini tekshiradi."""
    return text in get_button_variants(attr_name)
