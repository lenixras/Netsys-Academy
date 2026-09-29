FROM debian:trixie-slim
ARG FULL=0
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 bridge-utils iperf3 tcpdump jq curl python3 which \
    iputils-ping iputils-arping iputils-tracepath procps \
    ca-certificates \
    && (apt-get install -y --no-install-recommends mstpd || true) \
    && if [ "$FULL" != 0 ]; then apt-get install -y --no-install-recommends \
    bind9 bind9-dnsutils dnsmasq chrony snmpd snmp tshark \
    ansible-core python3-pytest openssh-client openssh-server sudo git nftables python3-yaml; fi \
    && if [ "$FULL" = 2 ]; then apt-get install -y --no-install-recommends \
    slapd ldap-utils postfix dovecot-imapd radvd \
    prometheus prometheus-node-exporter isc-dhcp-client isc-dhcp-relay; fi \
    && rm -rf /var/lib/apt/lists/*
CMD ["sleep", "infinity"]
