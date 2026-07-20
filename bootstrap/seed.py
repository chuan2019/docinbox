"""Idempotent seeding for docinbox resources.
Run with: python -m bootstrap.seed
Safe to run repeatedly - it converges, it doesn't depulicate.
"""
import secrets as pysecrets
from app.aws.clients import get_client
from app.config import get_settings

PARAMETERS: dict[str, str] = {
    "s3/bucket-name": "inbox-uploads",
    "llm/model-name": "llama3.2:3b",
    "features/email-digest": "false",
}

def seed_parameters(env: str) -> None:
    ssm = get_client("ssm")
    for suffix, value in PARAMETERS.items():
        name = f"/docinbox/{env}/{suffix}"
        # Overwrite=True makes this idempotent: re-seeding refreshes
        # values instead of failing with ParameterAlreadyExists.
        ssm.put_parameter(
            Name=name, Value=value,
            Type="String", Overwrite=True
        )
        print(f" param {name} = {value}")

def seed_signing_key(env: str) -> None:
    sm = get_client("secretsmanager")
    name = f"docinbox/{env}/signing-key"
    try:
        sm.create_secret(
            Name=name,
            SecretString=pysecrets.token_urlsafe(32)
        )
        print(f" secret {name} (created)")
    except sm.exceptions.ResourceExistsException:
        # Unlike parameters, we do NOT overwrite an existing secret:
        # a signing key that changes on every seed would invalidate
        # everything previously signed with it.
        print(f" secret {name} (already exists, kept)")

def main() -> None:
    env = get_settings().app_env
    print(f"Seeding docinbox resources for env '{env}' ...")
    seed_parameters(env)
    seed_signing_key(env)
    print("Done.")


if __name__ == "__main__":
    main()
