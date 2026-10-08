"""DCD Router — keyword-matching классификатор запроса по домену.

Generic version: 15 domains + ford-club (personal).
No customer-specific references.
"""

import re
from typing import Dict, List

# ─── Domain Configuration ──────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "linux-admin": {
        "weight": 3,
        "anti_keywords": ["nginx", "docker", "letsencrypt", "pytest", "async function",
                          "javascript", "react", "typescript", "git", "github",
                          "ci/cd", "redis", "postgresql", "kubernetes"],
        "keywords": {
            "systemd": 7, "systemctl": 6, "service": 4, "unit": 3, "timer": 4,
            "journalctl": 5, "logs": 2, "boot": 3, "startup": 3,
            "ssh": 4, "sshd": 4, "authorized_keys": 3, "keygen": 3,
            "sudo": 3, "visudo": 3, "useradd": 3, "groupadd": 3,
            "cron": 4, "crontab": 4, "at": 2, "systemd-timer": 4,
            "logrotate": 3, "rsyslog": 3, "syslog": 2,
            "mount": 3, "fstab": 3, "umount": 2, "lsblk": 3,
            "df": 2, "du": 2, "free": 2, "top": 2, "htop": 2,
            "iptables": 4, "nftables": 4, "firewall": 3, "ufw": 4,
            "selinux": 3, "auditd": 2, "apparmor": 2,
            "package": 2, "apt": 3, "yum": 3, "dnf": 3, "pacman": 3,
            "kernel": 2, "module": 2, "modprobe": 2, "lsmod": 2,
            "proc": 2, "sysctl": 4, "sysfs": 2,
        },
        "collections": ["linux-admin", "server-config"],
        "primary_source": "zvec",
        "fallback_sources": ["web"],
    },
    "networking": {
        "weight": 3,
        "anti_keywords": ["ansible", "terraform", "kubernetes", "helm", "docker compose"],
        "keywords": {
            "wireguard": 7, "wg": 5, "vpn": 4, "peer": 3, "endpoint": 3, "allowedips": 4,
            "openvpn": 5, "ipsec": 4, "strongswan": 4, "ike": 3,
            "bgp": 5, "ospf": 4, "isis": 3, "routing": 3, "router": 3,
            "vlan": 5, "trunk": 4, "access": 3, "802.1q": 4, "bridge": 3,
            "tcp": 2, "udp": 2, "ip": 2, "subnet": 3, "cidr": 3,
            "dns": 3, "bind": 3, "unbound": 3, "resolv": 2,
            "dhcp": 3, "dhcpd": 3, "pxe": 2,
            "load balancer": 4, "haproxy": 5, "nginx": 2, "proxy": 2,
            "firewall": 3, "iptables": 3, "nftables": 3, "ufw": 3,
            "mtu": 3, "fragmentation": 2, "jumbo": 2,
        },
        "collections": ["networking", "vpn-config"],
        "primary_source": "zvec",
        "fallback_sources": ["context7", "web"],
    },
    "devops": {
        "weight": 3,
        "anti_keywords": ["postgresql", "mysql", "redis"],
        "keywords": {
            "docker": 5, "container": 3, "image": 2, "dockerfile": 4,
            "docker compose": 6, "compose": 4, "stack": 3,
            "kubernetes": 5, "k8s": 5, "kubectl": 5, "pod": 3, "deployment": 4,
            "helm": 5, "chart": 4, "values": 3, "release": 2,
            "terraform": 5, "tf": 4, "plan": 3, "apply": 3, "state": 3, "module": 3,
            "ansible": 5, "playbook": 5, "role": 4, "inventory": 3, "task": 2,
            "ci/cd": 5, "pipeline": 4, "github actions": 4, "gitlab ci": 4, "jenkins": 4,
            "argo": 3, "argocd": 4, "flux": 3,
            "prometheus": 3, "grafana": 3, "alertmanager": 3,
            "logging": 2, "elk": 3, "loki": 3,
            "monitoring": 2, "observability": 2,
        },
        "collections": ["devops", "infra-as-code"],
        "primary_source": "context7",
        "fallback_sources": ["zvec", "web"],
    },
    "software-dev": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "terraform", "ansible", "prometheus", "grafana"],
        "keywords": {
            "python": 5, "pip": 3, "venv": 3, "poetry": 3, "uv": 3,
            "rust": 5, "cargo": 4, "crate": 3, "ownership": 4, "borrow": 4, "lifetime": 4,
            "go": 4, "golang": 4, "module": 3, "goroutine": 3, "channel": 3,
            "javascript": 3, "typescript": 4, "node": 3, "npm": 3, "yarn": 2,
            "react": 3, "vue": 3, "next": 3,
            "git": 3, "commit": 2, "branch": 2, "merge": 2, "rebase": 3, "pr": 3,
            "github": 2, "gitlab": 2,
            "testing": 3, "pytest": 4, "unit test": 3, "integration": 3,
            "lint": 3, "mypy": 3, "ruff": 3, "black": 3,
            "async": 3, "await": 3, "asyncio": 4,
            "api": 3, "rest": 3, "graphql": 3, "grpc": 3,
            "database": 2, "sql": 2, "orm": 3,
            "design pattern": 3, "solid": 3, "clean code": 3,
        },
        "collections": ["software-dev", "code-patterns"],
        "primary_source": "context7",
        "fallback_sources": ["zvec", "web"],
    },
    "database": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "docker compose", "terraform"],
        "keywords": {
            "postgresql": 7, "postgres": 6, "pg": 4,
            "база данных": 5, "бд": 4, "репликация": 5,
            "mysql": 5, "mariadb": 4,
            "redis": 5, "key-value": 3,
            "replication": 5, "streaming": 4, "wal": 5, "walreceiver": 5,
            "primary": 4, "standby": 4, "replica": 4, "failover": 4,
            "vacuum": 5, "autovacuum": 5, "analyze": 4, "bloat": 4, "freeze": 4,
            "index": 4, "btree": 3, "hash": 2, "gin": 3, "gist": 3,
            "query plan": 4,
            "transaction": 3, "isolation": 3, "lock": 3, "deadlock": 4,
            "backup": 3, "pg_dump": 4, "pg_basebackup": 4, "pitr": 4,
            "patroni": 5, "etcd": 3, "consul": 3,
            "connection pool": 4, "pgbouncer": 5,
        },
        "collections": ["database", "postgresql"],
        "primary_source": "zvec",
        "fallback_sources": ["context7", "web"],
    },
    "monitoring": {
        "weight": 3,
        "anti_keywords": ["ansible", "terraform", "kubernetes"],
        "keywords": {
            "prometheus": 6, "promql": 5, "alert": 4, "alertmanager": 4, "rule": 3,
            "grafana": 5, "dashboard": 4, "panel": 3, "variable": 3, "templating": 3,
            "metric": 3, "counter": 2, "gauge": 2, "histogram": 3, "summary": 3,
            "exporter": 4, "node_exporter": 4, "blackbox": 3,
            "loki": 4, "logql": 3, "log": 2,
            "tempo": 3, "trace": 3, "span": 2,
            "slack": 2, "pagerduty": 2, "opsgenie": 2,
            "slo": 3, "sli": 3, "error budget": 3,
        },
        "collections": ["monitoring", "observability"],
        "primary_source": "zvec",
        "fallback_sources": ["context7", "web"],
    },
    "security": {
        "weight": 3,
        "anti_keywords": ["ansible", "terraform", "kubernetes"],
        "keywords": {
            "cve": 5, "vulnerability": 5, "patch": 3, "security": 3,
            "ssh": 3, "key": 2, "certificate": 3, "tls": 3, "ssl": 3,
            "letsencrypt": 4, "certbot": 4, "acme": 3,
            "firewall": 3, "iptables": 3, "nftables": 3, "ufw": 3,
            "fail2ban": 4, "ban": 3, "brute force": 4,
            "audit": 3, "auditd": 3, "selinux": 3, "apparmor": 3,
            "encryption": 3, "gpg": 3, "age": 3, "sops": 4,
            "penetration": 3, "pentest": 3, "scan": 2,
            "compliance": 3, "cis": 3, "nist": 3,
        },
        "collections": ["security", "hardening"],
        "primary_source": "zvec",
        "fallback_sources": ["jira", "web"],
    },
    "storage": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "terraform"],
        "keywords": {
            "zfs": 6, "pool": 4, "dataset": 3, "raidz": 5, "raidz2": 5, "mirror": 4,
            "диск": 4, "диски": 4, "рейд": 5, "массив": 4, "хранилище": 4,
            "snapshot": 5, "send": 4, "receive": 4, "incremental": 4,
            "lvm": 4, "vg": 3, "lv": 3, "pv": 3,
            "ext4": 3, "xfs": 3, "btrfs": 4,
            "mount": 3, "fstab": 3, "umount": 2,
            "disk": 2, "ssd": 2, "nvme": 3, "hdd": 2,
            "raid": 4, "mdadm": 4,
            "backup": 3, "restore": 3, "borg": 4, "restic": 4,
            "nfs": 3, "smb": 3, "samba": 3,
        },
        "collections": ["storage", "filesystems"],
        "primary_source": "zvec",
        "fallback_sources": ["web"],
    },
    "virtualization": {
        "weight": 3,
        "anti_keywords": ["ansible", "terraform", "kubernetes"],
        "keywords": {
            "proxmox": 6, "pve": 5, "lxc": 5, "container": 3, "ct": 3,
            "qemu": 4, "kvm": 5, "libvirt": 4, "virsh": 4,
            "vm": 3, "virtual machine": 3,
            "gpu passthrough": 5, "vfio": 5, "iommu": 5, "vfio-pci": 5,
            "migration": 3, "live migration": 4,
            "backup": 3, "vzdump": 4, "restore": 3,
            "cluster": 3, "ha": 3, "fencing": 3,
            "ceph": 4, "rbd": 3,
        },
        "collections": ["virtualization", "proxmox"],
        "primary_source": "zvec",
        "fallback_sources": ["web"],
    },
    "email": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "terraform"],
        "keywords": {
            "postfix": 6, "dovecot": 6, "smtp": 4, "imap": 4, "pop3": 3,
            "почта": 5, "почтовый": 5, "спам": 5, "спам фильтр": 6,
            "sieve": 5, "filter": 3, "spam": 3, "rspamd": 4,
            "dkim": 5, "spf": 5, "dmarc": 5, "mx": 3,
            "mail": 2, "mailbox": 2, "maildir": 3,
            "alias": 2, "virtual": 3, "transport": 3,
            "queue": 2, "deferred": 2, "bounce": 2,
            "tls": 3, "starttls": 3, "smtps": 3,
            "stalwart": 5,
        },
        "collections": ["email", "mail-server"],
        "primary_source": "zvec",
        "fallback_sources": ["web"],
    },
    "kernel": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "docker"],
        "keywords": {
            "kernel": 6, "linux kernel": 6, "module": 4, "driver": 4,
            "sysctl": 5, "proc": 3, "sysfs": 3,
            "boot": 3, "grub": 3, "initramfs": 4, "dracut": 3,
            "oom": 3, "out of memory": 4,
            "panic": 4, "kdump": 3, "crash": 3,
            "trace": 3, "ftrace": 3, "perf": 4,
            "sched": 3, "cgroup": 3, "namespace": 3,
            "bpf": 4, "ebpf": 5, "tracepoint": 3,
            "interrupt": 3, "irq": 3, "softirq": 3,
        },
        "collections": ["kernel", "linux-internals"],
        "primary_source": "zvec",
        "fallback_sources": ["context7", "web"],
    },
    "scripting": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "terraform"],
        "keywords": {
            "bash": 6, "shell": 4, "sh": 3, "zsh": 3, "fish": 3,
            "script": 4, "scripting": 4,
            "find": 4, "grep": 4, "awk": 5, "sed": 4,
            "curl": 3, "wget": 3, "jq": 4, "yq": 3,
            "loop": 2, "if": 2, "case": 2, "function": 3,
            "variable": 2, "array": 3, "associative": 3,
            "pipe": 2, "redirect": 2, "stdin": 2, "stdout": 2, "stderr": 2,
            "cron": 3, "at": 2, "systemd timer": 3,
        },
        "collections": ["scripting", "automation"],
        "primary_source": "zvec",
        "fallback_sources": ["context7", "web"],
    },
    "docs": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "terraform"],
        "keywords": {
            "adr": 6, "architecture decision record": 6, "decision": 3,
            "documentation": 4, "docs": 3, "readme": 3,
            "markdown": 3, "md": 2, "rst": 2, "asciidoc": 2,
            "mkdocs": 4, "sphinx": 3, "hugo": 3,
            "diagram": 3, "mermaid": 4, "plantuml": 3,
            "template": 2, "style guide": 3,
        },
        "collections": ["docs", "architecture"],
        "primary_source": "zvec",
        "fallback_sources": ["confluence"],
    },
    "hardware": {
        "weight": 3,
        "anti_keywords": ["kubernetes", "ansible", "terraform"],
        "keywords": {
            "cpu": 3, "intel": 3, "amd": 3, "arm": 3,
            "memory": 3, "ram": 3, "ddr": 3, "ecc": 4,
            "disk": 3, "ssd": 3, "nvme": 4, "hdd": 2,
            "raid": 4, "mdadm": 4,
            "backup": 3, "restore": 3, "borg": 4, "restic": 4,
            "nfs": 3, "smb": 3, "samba": 3,
        },
        "collections": ["hardware", "server-hardware"],
        "primary_source": "zvec",
        "fallback_sources": ["web"],
    },
    "ford-club": {
        "weight": 3,
        "anti_keywords": ["linux", "kubernetes", "ansible", "terraform", "docker", "postgresql"],
        "keywords": {
            "ford": 7, "explorer": 6, "focus": 5, "fiesta": 5, "mondeo": 5,
            "kuga": 5, "ecosport": 5, "mustang": 5, "ranger": 5,
            "шрус": 7, "подшипник": 6, "амортизатор": 6, "резина": 4, "диск": 4,
            "подвеска": 5, "рулевое": 5, "тормоза": 5, "колодки": 5, "диски": 4,
            "масло": 5, "фильтр": 4, "свечи": 5, "ремень": 5, "цепь": 4,
            "дтп": 3, "страховка": 3, "каско": 3, "осаго": 3,
            "vin": 4, "каталог": 4, "oem": 5, "партномер": 6, "oem номер": 6,
            "эталон": 3, "оригинал": 4, "аналог": 3,
        },
        "collections": ["ford-club", "auto-parts"],
        "primary_source": "zvec",
        "fallback_sources": ["web"],
    },
    "web-research": {
        "weight": 3,
        # продуктовые запросы (astra/termidesk и т.п.) не должны утекать в веб —
        # их домены сильнее; anti ещё и от typeof-мусора
        "anti_keywords": ["astra", "termidesk", "aldpro", "ald pro", "rupost",
                          "systemd", "kubernetes", "postgresql", "rust",
                          "nginx", "docker", "git"],
        "keywords": {
            "погугли": 6, "найди в сети": 6,
            "актуальн": 5,
            "интернет": 3, "веб": 3, "online": 3,
            "цена": 4, "купить": 4, "свеж": 4, "обзор": 4, "сравни": 4,
            "отзывы": 4, "новости": 4, "latest": 4,
        },
        "collections": ["webcache"],
        "primary_source": "webcache",
        "fallback_sources": ["webcache", "web", "wiki"],
    },
}

# ─── Helper Functions ──────────────────────────────────────────────

# Keep this deliberately small and domain-specific. It handles the common
# inflections of the Russian keywords below without introducing a morphology
# dependency or broad, error-prone suffix stripping.
CYRILLIC_TOKEN_ALIASES = {
    "базы": "база",
    "базе": "база",
    "базу": "база",
    "базой": "база",
    "данные": "данных",
    "данными": "данных",
    "репликации": "репликация",
    "репликацию": "репликация",
    "репликацией": "репликация",
    "почты": "почта",
    "почте": "почта",
    "почту": "почта",
    "почтой": "почта",
    "диска": "диск",
    "диске": "диск",
    "дисков": "диск",
    "диском": "диск",
    "рейда": "рейд",
    "рейде": "рейд",
    "рейдом": "рейд",
}

def _stem(word: str) -> str:
    return CYRILLIC_TOKEN_ALIASES.get(word.lower().strip(), word.lower().strip())

def _normalize(text: str) -> str:
    return re.sub(r'[^\w\s\-]', ' ', text.lower())

def _extract_tokens(text: str) -> List[str]:
    normalized = _normalize(text)
    tokens = [_stem(token) for token in normalized.split()]
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)]
    return tokens + bigrams

def _score_domain(tokens: List[str], domain_data: Dict) -> tuple:
    keywords = domain_data.get("keywords", {})
    anti = domain_data.get("anti_keywords", [])
    weight = domain_data.get("weight", 1)

    score = 0.0
    matched = []
    text_lower = " ".join(tokens)

    def _matches(kw: str, text: str) -> bool:
        """Match keyword with word boundaries to avoid substring false positives.

        For multi-word keywords (e.g. 'docker compose') or keywords containing
        non-word chars (e.g. '802.1q', 'ci/cd'), fall back to substring match
        because \b doesn't behave intuitively across punctuation.
        """
        if not kw:
            return False
        if re.search(r'[^A-Za-z0-9_]', kw):
            return kw in text
        return re.search(r'\b' + re.escape(kw) + r'\b', text) is not None

    for kw, kw_weight in keywords.items():
        if _matches(kw, text_lower):
            score += kw_weight * weight
            matched.append(kw)

    for anti_kw in anti:
        if _matches(anti_kw, text_lower):
            score *= 0.3  # penalty

    return score, matched

# ─── Main Classification Function ──────────────────────────────────

def classify(query: str) -> Dict:
    """Классифицировать запрос по домену, коллекции и источнику.

    Returns: {
        "domain": str,
        "collection": str,
        "confidence": float,
        "keywords_matched": list,
        "fallback": bool,
        "router": "keyword",
        "primary_source": str,
        "fallback_sources": list,
    }
    """
    tokens = _extract_tokens(query)
    if not tokens:
        return {
            "domain": "software-dev",
            "collection": "general",
            "confidence": 0.0,
            "keywords_matched": [],
            "fallback": True,
            "router": "keyword",
            "primary_source": "zvec",
            "fallback_sources": ["web"],
        }

    # Pricing/fact verification over several named services must go to the
    # live web, not to a local domain. A list of tech brand names plus price
    # words looks like a work topic to keyword scoring and was misrouted to
    # devops (live case 2026-08-22: ScraperAPI/Tavily/2Captcha tariffs).
    # Exception: if a strong product anchor (postgresql, docker, ford...) is
    # present, the product domains win - their anti_keywords already push
    # web-research down. Only "orphan brands" (no local home) get forced here.
    _PRICE_WORDS = ("цена", "цены", "цену", "тариф", "тарифы", "прайс",
                    "стоит", "стоимость", "pricing", "сколько стоит")
    q_lower = query.lower()
    has_price_word = any(w in q_lower for w in _PRICE_WORDS)
    if has_price_word:
        _anchors = set()
        for _d, _data in DOMAIN_KEYWORDS.items():
            for _kw in _data.get("anti_keywords", []):
                _anchors.add(_kw.lower())
            if _d == "web-research":
                continue
            for _kw, _w in _data.get("keywords", {}).items():
                if _w >= 5:
                    _anchors.add(_kw.lower())
        brand_tokens = [t for t in tokens
                        if any(c.isascii() and c.isalpha() for c in t)
                        and not any(a in t for a in _anchors)]
        if len(brand_tokens) >= 2:
            wr = DOMAIN_KEYWORDS["web-research"]
            return {
                "domain": "web-research",
                "collection": wr.get("collections", ["webcache"])[0],
                "confidence": 0.95,
                "keywords_matched": ["price-verification"],
                "fallback": False,
                "router": "keyword",
                "primary_source": wr.get("primary_source", "webcache"),
                "fallback_sources": wr.get("fallback_sources", ["webcache", "web"]),
            }

    best_domain = "software-dev"
    best_score = 0.0
    best_matched = []
    runner_up_score = 0.0

    for domain, data in DOMAIN_KEYWORDS.items():
        score, matched = _score_domain(tokens, data)
        if score > best_score:
            runner_up_score = best_score
            best_score = score
            best_domain = domain
            best_matched = matched
        elif score > runner_up_score:
            runner_up_score = score

    # Confidence is evidence-based, not dictionary-size-based. The previous
    # denominator was the sum of every keyword in a domain, so even a precise
    # "postgresql streaming replication" routed with 0.098 confidence.
    # Strong/multiple matches raise confidence; a close runner-up lowers it.
    best_data = DOMAIN_KEYWORDS[best_domain]
    domain_weight = best_data.get("weight", 1)
    strength = min(best_score / max(domain_weight * 8, 1), 1.0)
    coverage = min(len(best_matched) / 3.0, 1.0)
    margin = (best_score - runner_up_score) / best_score if best_score else 0.0
    confidence = (0.5 * strength + 0.5 * coverage) * (0.7 + 0.3 * margin)

    domain_data = DOMAIN_KEYWORDS[best_domain]
    collections = domain_data.get("collections", ["general"])
    collection = collections[0]

    return {
        "domain": best_domain,
        "collection": collection,
        "confidence": round(confidence, 3),
        "keywords_matched": best_matched[:10],
        "fallback": confidence < 0.3,
        "router": "keyword",
        "primary_source": domain_data.get("primary_source", "zvec"),
        "fallback_sources": domain_data.get("fallback_sources", ["web"]),
    }

if __name__ == "__main__":
    test_queries = [
        "как настроить postgresql streaming replication",
        "rust ownership borrow checker",
        "шрус ford explorer 2016 партномер",
        "nginx reverse proxy ssl letsencrypt",
        "wireguard vpn config",
        "systemd service unit timer",
        "docker compose up production",
        "kubernetes deployment helm chart",
    ]
    for q in test_queries:
        result = classify(q)
        print(f"{q:50s} -> {result['domain']:15s} ({result['confidence']:.2f}) {result['keywords_matched'][:3]}")