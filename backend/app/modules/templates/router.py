"""HTTP-эндпойнты шаблонов."""

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.modules.templates import service
from app.modules.templates.models import EmailTemplate
from app.modules.templates.schemas import (
    PreviewRequest,
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
)

router = APIRouter()


@router.get("", response_model=list[TemplateRead])
def list_all(db: DbSession, user: CurrentUser) -> list[TemplateRead]:
    return [TemplateRead.model_validate(t) for t in service.list_templates(db)]


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create(payload: TemplateCreate, db: DbSession, user: CurrentUser) -> TemplateRead:
    variables = payload.variables or service.extract_variables(payload.html_body)
    template = EmailTemplate(
        name=payload.name,
        subject=payload.subject,
        html_body=payload.html_body,
        text_body=payload.text_body,
        variables=variables,
        created_by_id=user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return TemplateRead.model_validate(template)


@router.get("/{template_id}", response_model=TemplateRead)
def get(template_id: int, db: DbSession, user: CurrentUser) -> TemplateRead:
    template = service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")
    return TemplateRead.model_validate(template)


@router.patch("/{template_id}", response_model=TemplateRead)
def update(
    template_id: int, payload: TemplateUpdate, db: DbSession, user: CurrentUser
) -> TemplateRead:
    template = service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    template.version += 1
    db.commit()
    db.refresh(template)
    return TemplateRead.model_validate(template)


@router.post("/{template_id}/preview")
def preview(template_id: int, payload: PreviewRequest, db: DbSession, user: CurrentUser) -> dict:
    template = service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")

    try:
        subject, html, text = service.render_subject_and_body(template, payload.variables)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return {"subject": subject, "html": html, "text": text}
