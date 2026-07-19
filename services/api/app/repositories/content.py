"""Repository for ContentTemplate and TemplateVersion entities."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentTemplate, ProviderEnum, TemplateVersion


class ContentTemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        platform: ProviderEnum | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContentTemplate]:
        stmt = select(ContentTemplate).where(
            ContentTemplate.organization_id == org_id,
        )
        if platform is not None:
            stmt = stmt.where(ContentTemplate.platform == platform)
        stmt = stmt.order_by(ContentTemplate.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, org_id: uuid.UUID, template_id: uuid.UUID) -> ContentTemplate | None:
        result = await self.db.execute(
            select(ContentTemplate).where(
                ContentTemplate.organization_id == org_id,
                ContentTemplate.id == template_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, org_id: uuid.UUID, **fields) -> ContentTemplate:
        template = ContentTemplate(organization_id=org_id, version=1, **fields)
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)

        tv = TemplateVersion(
            template_id=template.id,
            version=1,
            title_template=template.title_template,
            body_template=template.body_template,
        )
        self.db.add(tv)
        await self.db.flush()

        return template

    async def update(self, template: ContentTemplate, **fields) -> ContentTemplate:
        needs_version = False
        for key in ("title_template", "body_template"):
            if key in fields and fields[key] != getattr(template, key):
                needs_version = True
                break

        for key, value in fields.items():
            setattr(template, key, value)

        if needs_version:
            template.version = (template.version or 1) + 1
            tv = TemplateVersion(
                template_id=template.id,
                version=template.version,
                title_template=template.title_template,
                body_template=template.body_template,
            )
            self.db.add(tv)

        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete(self, template: ContentTemplate) -> None:
        await self.db.delete(template)
        await self.db.flush()
