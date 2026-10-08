"""Compound query detection.

Moved out of rag_async.py (god module decomposition, audit P1). Pure function:
given a query + dcd result, return a list of sub-queries, or [] if not compound.
No I/O, no global state.
"""
from __future__ import annotations

_COMPOUND_PRODUCT_WORDS = {
    "ald", "aldpro", "ald pro", "rupost", "termidesk", "workspad", "ddo",
    "msad", "keycloak", "alse", "astra linux", "astra",
    "альд", "альд про", "рупост", "термидеск", "воркспад", "астра линукс",
    "астра", "кейклок",
}
_COMPOUND_INFRA_WORDS = {
    "postgresql", "postgres", "nginx", "redis", "docker", "kubernetes", "k8s",
    "patroni", "etcd", "haproxy", "prometheus", "grafana", "rabbitmq", "kafka",
    "ansible", "terraform", "salt", "saltstack", "sssd", "freeipa", "ipa",
    "msad", "ad", "active directory", "samba", "kerberos", "hbac", "rbac",
    "zabbix", "monitoring", "миграц", "доверен", "trust", "dhcp", "dns",
    "automation", "web оснастк", "web интерфейс", "web консоль",
    "постгрес", "постгре", "нжинкс", "докер", "кубер", "кубернетес", "патрони",
    "реплик", "репликация", "бд", "база данных", "резервн", "бэкап",
}


def detect_compound(query: str, dcd: dict | None = None) -> list[dict]:
    """Detect compound queries with keywords from multiple domains.

    Returns list of sub-queries, or empty list if not compound.
    Each sub-query: {"query": str, "domain": str, "collection": str}
    """
    ql = query.lower()
    has_product = any(w in ql for w in _COMPOUND_PRODUCT_WORDS)
    has_infra = any(w in ql for w in _COMPOUND_INFRA_WORDS)

    if not (has_product and has_infra):
        return []

    subqueries = []
    if has_product:
        subqueries.append({"query": query, "domain": "astra-products",
                           "collection": "astra-products"})
    if has_infra:
        infra_terms = [w for w in _COMPOUND_INFRA_WORDS if w in ql]
        infra_query = f"{query} {' '.join(infra_terms[:3])}" if infra_terms else query
        subqueries.append({"query": infra_query, "domain": "devops",
                           "collection": "deployment"})
    return subqueries