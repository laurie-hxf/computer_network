import argparse
import ipaddress

from scapy.all import *
from scapy.layers.inet import ICMP, IP
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest, ICMPv6PacketTooBig


def pmtu(dest_addr: str, use_ipv6: bool = False, src_addr: str = None) -> int:
    """
    Discover the Path MTU (PMTU) to the specified destination address.

    Args:
        dest_addr (str): The destination IP address to probe.
        use_ipv6 (bool): Flag indicating whether to use IPv6 or IPv4.
                         Your code should first check whether the address
                         is valid. Given an IPv4 address together with
                         `use_ipv6` set to True is NOT valid.
                         In this case, the function should raise a RuntimeError.
        src_addr (str): The source IP address to use for sending packets.

    Returns:
        An integer value indicating the PMTU detection result.

    Raises:
        RuntimeError: If the address is invalid.
    """
    # Validate the destination address
    if use_ipv6:
        if not (ipaddress.IPv6Address(dest_addr) if ':' in dest_addr else False):
            raise RuntimeError("Invalid IPv6 address or mismatch in address type.")
    else:
        if not (ipaddress.IPv4Address(dest_addr) if '.' in dest_addr else False):
            raise RuntimeError("Invalid IPv4 address or mismatch in address type.")

    # Define initial parameters
    min_mtu = 1280 if use_ipv6 else 50
    max_mtu = 1500
    detected_mtu = (min_mtu + max_mtu) // 2

    while min_mtu <= max_mtu:
        mid_mtu = (min_mtu + max_mtu) // 2

        # Construct the packet with the specified MTU size
        payload = b"X" * (mid_mtu - 48 if use_ipv6 else mid_mtu - 28)
        pkt = IPv6(src=src_addr, dst=dest_addr) / ICMPv6EchoRequest() / payload if use_ipv6 else IP(src=src_addr,
                                                                                                    dst=dest_addr,
                                                                                                    flags="DF") / ICMP() / payload

        # Send the packet and wait for a response
        response = sr1(pkt, timeout=5, verbose=False)
        if use_ipv6:
            if response is None:
                # No response means the packet is Successful delivery
                min_mtu = mid_mtu + 1
                detected_mtu = mid_mtu
            elif response.haslayer(ICMPv6PacketTooBig):
                max_mtu = mid_mtu - 1
                detected_mtu = mid_mtu - 1
            else:
                # Successful delivery
                detected_mtu = mid_mtu
                min_mtu = mid_mtu + 1

        else:
            if response is None:
                # No response means the packet was dropped (MTU is too large)
                max_mtu = mid_mtu - 1
            elif response.haslayer(ICMP) and response[ICMP].type in [3, 2]:
                # "Fragmentation Needed" or "Packet Too Big"
                if use_ipv6 or response[ICMP].code == 4:
                    max_mtu = mid_mtu - 1
                else:
                    min_mtu = mid_mtu + 1
            else:
                # Successful delivery
                detected_mtu = mid_mtu
                min_mtu = mid_mtu + 1

    return detected_mtu


def main():
    parser = argparse.ArgumentParser(description='Discover the Path MTU along a network path.')
    parser.add_argument('destination', type=str, help='The destination IP address to probe.')
    parser.add_argument('--ipv6', action='store_true', help='Use IPv6 instead of IPv4.')
    parser.add_argument('--source', type=str, help='Optional source IP address to use for probing.')

    args = parser.parse_args()

    try:
        # Call the PMTU discovery function
        mtu = pmtu(dest_addr=args.destination, use_ipv6=args.ipv6, src_addr=args.source)
        print(f"The Path MTU to {args.destination} is {mtu} bytes.")
    except RuntimeError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
