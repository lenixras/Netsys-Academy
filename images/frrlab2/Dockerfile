FROM frrouting/frr:latest
# bgpd + staticd + ospfd activés : M21 enseigne BGP (vtysh), pas le bootstrap des démons
RUN touch /etc/frr/vtysh.conf \
    && sed -i -e "s/^bgpd=no/bgpd=yes/" -e "s/^ospfd=no/ospfd=yes/" -e "s/^staticd=no/staticd=yes/" /etc/frr/daemons
