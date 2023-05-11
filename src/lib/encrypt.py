from pathlib import Path

import fitz


def encrypt_pdf(doc_path: str, user_password: str, owner_password: str = None, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY # always use this
        | fitz.PDF_PERM_PRINT # permit printing
        | fitz.PDF_PERM_COPY # permit copying
        | fitz.PDF_PERM_ANNOTATE # permit annotations
    )
    encrypt_meth = fitz.PDF_ENCRYPT_AES_256 # strongest algorithm
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[encrypt].pdf")
    doc.save(
        output_path,
        encryption=encrypt_meth, # set the encryption method
        owner_pw=owner_password, # set the owner password
        user_pw=user_password, # set the user password
        permissions=perm, # set permissions
    )

def decrypt_pdf(doc_path: str, password: str, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if doc.isEncrypted:
        doc.authenticate(password)
        n = doc.page_count
        doc.select(range(n))
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[decrypt].pdf")
    doc.save(output_path)

