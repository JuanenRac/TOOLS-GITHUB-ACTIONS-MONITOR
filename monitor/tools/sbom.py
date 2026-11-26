# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two software bills of materials of a release, CycloneDX 1.5 and SPDX 2.3, both in JSON, made with the standard library only and with nothing that changes from one build to the next: the same
zip gives the same two documents byte for byte (the time is fixed and the identifiers come from the SHA-256 of the zip).

The product needs no package: what both documents list are the files of the zip (with their SHA-256) and the optional libraries a person may install (each one unlocks something and nothing breaks without it).
"""
import hashlib
import json
import uuid

CDX_NAME = "github_actions_monitor.cdx.json"
SPDX_NAME = "github_actions_monitor.spdx.json"
PRODUCT = "github-actions-monitor"
SUPPLIER = "JuanenRac (Electro Hobby 3D)"
LICENSE_ID = "GPL-3.0-or-later"
HOME = "https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR"
FIXED_TIME = "2026-01-01T00:00:00Z"      # the same fixed moment the members of the zip carry
#: (name on PyPI, what it unlocks). None of them travels in the zip.
OPTIONAL = (("cryptography", "sealed backups and bundles (AES-256-GCM)"), ("rich", "the terminal view"), ("textual", "the full-screen terminal view"))
NOTE = "Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>"


def file_hashes(entries):
    """[(name, sha256 hex, sha1 hex)] of the members of the zip, sorted by name (SPDX asks for the SHA-1 of every file besides)."""
    return [(name, hashlib.sha256(data).hexdigest(), hashlib.sha1(data).hexdigest()) for name, data in sorted(entries.items())]


def serial(zip_sha, kind):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{HOME}#{kind}-{zip_sha}"))


def cyclonedx(version, zip_name, zip_sha, entries):
    components = [{"type": "file", "bom-ref": "file:" + name, "name": name, "hashes": [{"alg": "SHA-256", "content": sha}]} for name, sha, _ in file_hashes(entries)]
    components += [{"type": "library", "bom-ref": "pkg:pypi/" + name, "name": name, "scope": "optional", "description": what, "purl": "pkg:pypi/" + name} for name, what in OPTIONAL]
    root = {"type": "application", "bom-ref": PRODUCT, "name": PRODUCT, "version": version, "supplier": {"name": SUPPLIER}, "licenses": [{"license": {"id": LICENSE_ID}}],
            "hashes": [{"alg": "SHA-256", "content": zip_sha}], "externalReferences": [{"type": "vcs", "url": HOME}], "properties": [{"name": "distribution:file", "value": zip_name}]}
    return {"_author": NOTE, "_license": LICENSE_ID + " - see LICENSE", "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": "urn:uuid:" + serial(zip_sha, "cyclonedx"), "version": 1,
            "metadata": {"timestamp": FIXED_TIME, "component": root}, "components": components,
            "dependencies": [{"ref": PRODUCT, "dependsOn": ["pkg:pypi/" + name for name, _ in OPTIONAL]}]}


def spdx(version, zip_name, zip_sha, entries):
    files, relationships, sha1s = [], [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": "SPDXRef-Product"}], []
    for number, (name, sha, sha1) in enumerate(file_hashes(entries), 1):
        ref = f"SPDXRef-File-{number}"
        sha1s.append(sha1)
        files.append({"SPDXID": ref, "fileName": "./" + name, "checksums": [{"algorithm": "SHA1", "checksumValue": sha1}, {"algorithm": "SHA256", "checksumValue": sha}],
                      "licenseConcluded": "NOASSERTION", "copyrightText": "NOASSERTION"})
        relationships.append({"spdxElementId": "SPDXRef-Product", "relationshipType": "CONTAINS", "relatedSpdxElement": ref})
    packages = [{"SPDXID": "SPDXRef-Product", "name": PRODUCT, "versionInfo": version, "packageFileName": zip_name, "supplier": "Organization: " + SUPPLIER, "downloadLocation": HOME,
                 "licenseConcluded": LICENSE_ID, "licenseDeclared": LICENSE_ID, "copyrightText": NOTE, "checksums": [{"algorithm": "SHA256", "checksumValue": zip_sha}],
                 "filesAnalyzed": True, "packageVerificationCode": {"packageVerificationCodeValue": hashlib.sha1("".join(sorted(sha1s)).encode("ascii")).hexdigest()}}]
    for name, what in OPTIONAL:
        ref = "SPDXRef-Optional-" + name
        packages.append({"SPDXID": ref, "name": name, "downloadLocation": "NOASSERTION", "filesAnalyzed": False, "comment": "optional: " + what,
                         "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl", "referenceLocator": "pkg:pypi/" + name}]})
        relationships.append({"spdxElementId": ref, "relationshipType": "OPTIONAL_DEPENDENCY_OF", "relatedSpdxElement": "SPDXRef-Product"})
    return {"_author": NOTE, "_license": LICENSE_ID + " - see LICENSE", "spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT", "name": f"{PRODUCT}-{version}",
            "documentNamespace": f"{HOME}/spdx/{serial(zip_sha, 'spdx')}", "creationInfo": {"created": FIXED_TIME, "creators": ["Organization: " + SUPPLIER, "Tool: make_release.py"]},
            "packages": packages, "files": files, "relationships": relationships}


def documents(version, zip_name, zip_sha, entries):
    """{file name: bytes} of the two documents."""
    made = {CDX_NAME: cyclonedx(version, zip_name, zip_sha, entries), SPDX_NAME: spdx(version, zip_name, zip_sha, entries)}
    return {name: (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8") for name, doc in made.items()}
