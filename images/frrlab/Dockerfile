FROM frrouting/frr:latest
# ospfd activé au build : le lab M6 porte sur la config OSPF (vtysh), pas sur le bootstrap des démons
RUN touch /etc/frr/vtysh.conf \
    && sed -i -e 's/^ospfd=no/ospfd=yes/' -e 's/^staticd=no/staticd=yes/' /etc/frr/daemons
