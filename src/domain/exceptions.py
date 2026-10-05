class DomainError(Exception): ...


class BusinessLogicError(DomainError): ...


class LanguageModelError(DomainError): ...


class InsufficientFunds(BusinessLogicError):
    def __init__(self):
        super().__init__("Не хватает токенов! Пополнить баланс - /bal")


class RecordNotFound(DomainError):
    def __init__(self, desired):
        super().__init__(f"{desired} не найден в репозитории")


class ContextEmpty(BusinessLogicError):
    def __init__(self):
        super().__init__("Контекст пуст!")


class UndefinedDefendant(BusinessLogicError):
    def __init__(self):
        super().__init__("Подзащитный не определён!")


class UnknownDefendant(BusinessLogicError):
    def __init__(self):
        super().__init__("Этого участника нет в переписке. Напишите /go и выберите снова")


class UnexpectedError(BusinessLogicError):
    def __init__(self):
        super().__init__("Ошибка! Обратитесь в техподдержку")


class MessagesLimitExceeded(BusinessLogicError):
    def __init__(self, limit: int):
        super().__init__(f"Превышен лимит сообщений! ({limit})")


class ContextLimitExceeded(BusinessLogicError):
    def __init__(self, limit: int):
        super().__init__(
            f"Спор стал слишком длинным для модели ({limit} символов). "
            "Напишите /clear и начните заново"
        )


class MediaLimitExceeded(BusinessLogicError):
    def __init__(self, limit: int):
        super().__init__(f"Превышен лимит длительности медиа! ({limit} секунд)")
