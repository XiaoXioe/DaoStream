from .wordpress_theme import WordPressThemeSource

class AnichinSource(WordPressThemeSource):
    @property
    def name(self) -> str:
        return "Anichin"

    @property
    def base_url(self) -> str:
        return "https://anichin.moe"
