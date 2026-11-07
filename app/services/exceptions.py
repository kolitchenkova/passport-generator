"""Исключения сервисного слоя приложения."""


class PassportServiceError(Exception):
    """Базовое исключение для сервиса паспортов."""

    pass


class ProductNotFoundError(PassportServiceError):
    """Изделие не найдено в базе данных."""

    pass


class TemplateNotFoundError(PassportServiceError):
    """Шаблон не найден или отключен."""

    pass


class IncompleteParametersError(PassportServiceError):
    """Бизнес-правило 1: у изделия отсутствуют обязательные параметры шаблона."""

    def __init__(self, missing_parameters: list[str]):
        self.missing_parameters = missing_parameters
        msg = f"Отсутствуют обязательные параметры изделия: {', '.join(missing_parameters)}"
        super().__init__(msg)


class PassportRenderError(PassportServiceError):
    """Бизнес-правило 3: сбой при рендеринге документа DOCX."""

    pass
