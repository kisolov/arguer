from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    __test__ = False  # настройки, а не набор тестов
