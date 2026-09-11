"""Работа с шаблонами: рендер через Jinja2, CRUD."""

from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError, meta, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.templates.models import EmailTemplate

_jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_source: str, variables: dict[str, Any]) -> str:
    """Отрисовать шаблон с переданными переменными."""
    tmpl = _jinja_env.from_string(template_source)
    return tmpl.render(**variables)


def extract_variables(template_source: str) -> list[str]:
    """Найти все переменные, использованные в шаблоне."""
    ast = _jinja_env.parse(template_source)
    return sorted(meta.find_undeclared_variables(ast))


def render_subject_and_body(
    template: EmailTemplate, variables: dict[str, Any]
) -> tuple[str, str, str | None]:
    try:
        subject = render(template.subject, variables)
        html = render(template.html_body, variables)
        text = render(template.text_body, variables) if template.text_body else None
    except TemplateError as e:
        raise ValueError(f"Ошибка рендеринга шаблона: {e}") from e
    return subject, html, text


def list_templates(db: Session) -> list[EmailTemplate]:
    return list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.updated_at.desc())).all())


def get_template(db: Session, template_id: int) -> EmailTemplate | None:
    return db.get(EmailTemplate, template_id)
