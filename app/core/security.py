from pwdlib import PasswordHash


# Create one reusable password-hashing object.
#
# PasswordHash.recommended() selects pwdlib's currently recommended
# password-hashing algorithm and configuration.
#
# We create this object once instead of rebuilding it every time
# a customer registers.
password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """
    Convert a plain-text password into a secure one-way hash.

    The plain password exists only while processing the request.
    We return the generated hash so that only the hash is stored
    in PostgreSQL.
    """

    return password_hash.hash(plain_password)
