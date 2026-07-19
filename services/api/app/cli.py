"""Typer CLI for admin operations: create-owner, create-organization, create-user."""

import asyncio

import structlog
import typer

from app.database import get_async_session_local
from app.models import MembershipRole
from app.repositories import UserRepository
from app.repositories.organization import OrganizationRepository

app_cli = typer.Typer(name="realestate-cli")
logger = structlog.get_logger(__name__)


async def _create_owner(
    email: str,
    full_name: str,
    password: str,
    org_name: str,
    org_slug: str,
) -> None:
    async with get_async_session_local()() as db:
        user_repo = UserRepository(db)
        org_repo = OrganizationRepository(db)

        # Create user
        existing = await user_repo.get_by_email(email)
        if existing:
            typer.echo(f"User {email} already exists with id {existing.id}")
            user = existing
        else:
            user = await user_repo.create(email=email, full_name=full_name, password=password)
            typer.echo(f"Created user: {user.id} ({user.email})")

        # Create org
        existing_org = await org_repo.get_by_slug(org_slug)
        if existing_org:
            typer.echo(f"Organization {org_slug} already exists with id {existing_org.id}")
            org = existing_org
        else:
            org = await org_repo.create(name=org_name, slug=org_slug)
            typer.echo(f"Created organization: {org.id} ({org.slug})")

        # Add owner membership
        existing_membership = await org_repo.get_membership(org.id, user.id)
        if existing_membership:
            if existing_membership.role != MembershipRole.owner:
                existing_membership.role = MembershipRole.owner
                await db.flush()
                typer.echo(f"Updated role to owner for {email} in {org_slug}")
            else:
                typer.echo(f"User {email} is already owner of {org_slug}")
        else:
            await org_repo.add_member(org, user, MembershipRole.owner)
            typer.echo(f"Added {email} as owner of {org_slug}")

        await db.commit()


@app_cli.command("create-owner")
def create_owner(
    email: str = typer.Argument(..., help="Owner email"),
    full_name: str = typer.Argument(..., help="Owner full name"),
    password: str = typer.Option(
        None, "--password", "-p", help="Password (will prompt if not provided)"
    ),
    org_name: str = typer.Option(..., "--org-name", help="Organization name"),
    org_slug: str = typer.Option(..., "--org-slug", help="Organization slug"),
) -> None:
    """Create an owner user with an organization."""
    pw = password or typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    asyncio.run(_create_owner(email, full_name, pw, org_name, org_slug))


async def _create_organization(
    owner_email: str,
    name: str,
    slug: str,
) -> None:
    async with get_async_session_local()() as db:
        user_repo = UserRepository(db)
        org_repo = OrganizationRepository(db)

        owner = await user_repo.get_by_email(owner_email)
        if not owner:
            typer.echo(f"Error: user {owner_email} not found", err=True)
            raise typer.Exit(code=1)

        existing_org = await org_repo.get_by_slug(slug)
        if existing_org:
            typer.echo(f"Error: organization slug '{slug}' already exists", err=True)
            raise typer.Exit(code=1)

        org = await org_repo.create(name=name, slug=slug)
        await org_repo.add_member(org, owner, MembershipRole.owner)
        await db.commit()

        typer.echo(f"Created organization '{org.slug}' with owner {owner_email}")


@app_cli.command("create-organization")
def create_organization(
    owner_email: str = typer.Argument(..., help="Email of the owner user"),
    name: str = typer.Argument(..., help="Organization name"),
    slug: str = typer.Argument(..., help="Organization slug"),
) -> None:
    """Create an organization with an existing user as owner."""
    asyncio.run(_create_organization(owner_email, name, slug))


async def _create_user(
    email: str,
    full_name: str,
    password: str,
    role: str,
    org_slug: str,
) -> None:
    async with get_async_session_local()() as db:
        user_repo = UserRepository(db)
        org_repo = OrganizationRepository(db)

        org = await org_repo.get_by_slug(org_slug)
        if not org:
            typer.echo(f"Error: organization slug '{org_slug}' not found", err=True)
            raise typer.Exit(code=1)

        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            typer.echo(f"User {email} already exists with id {existing_user.id}")
            user = existing_user
        else:
            user = await user_repo.create(email=email, full_name=full_name, password=password)
            typer.echo(f"Created user: {user.id} ({user.email})")

        # Check and add membership
        existing_membership = await org_repo.get_membership(org.id, user.id)
        if existing_membership:
            typer.echo(
                f"User {email} is already a member of {org_slug} as {existing_membership.role.value}"
            )
        else:
            membership_role = MembershipRole(role)
            await org_repo.add_member(org, user, membership_role)
            typer.echo(f"Added {email} to {org_slug} as {role}")

        await db.commit()


@app_cli.command("create-user")
def create_user(
    email: str = typer.Argument(..., help="User email"),
    full_name: str = typer.Argument(..., help="User full name"),
    password: str = typer.Option(
        None, "--password", "-p", help="Password (will prompt if not provided)"
    ),
    role: str = typer.Option("viewer", "--role", "-r", help="Role: owner, administrator, editor, viewer"),
    org_slug: str = typer.Option(..., "--org-slug", help="Organization slug"),
) -> None:
    """Create a user with membership in an existing organization."""
    pw = password or typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    valid_roles = {r.value for r in MembershipRole}
    if role not in valid_roles:
        typer.echo(f"Error: invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}", err=True)
        raise typer.Exit(code=1)
    asyncio.run(_create_user(email, full_name, pw, role, org_slug))


if __name__ == "__main__":
    app_cli()
