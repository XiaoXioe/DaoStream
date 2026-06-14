from .wordpress_theme import WordPressThemeSource

class AnimexinSource(WordPressThemeSource):
    @property
    def name(self) -> str:
        return "AnimeXin"

    @property
    def base_url(self) -> str:
        return "https://animexin.dev"
