#!/usr/bin/env python3
"""
Serial Nice Power supply locator + initializer.

- Discovers COM/serial ports
- Probes for Nice Power supplies (both Modbus and D2001 custom protocol)
- Initializes appropriate NicePowerSupply instances
- Exposes getters that return ready instances or empty list if none found
"""

from __future__ import annotations
from typing import List, Tuple, Optional
from serial.tools import list_ports
from NICE_POWER_SPPS_D8001_232 import NicePowerSupply as NicePowerModbus
from NICE_POWER_SPPS_D2001_232 import NicePowerSupply as NicePowerD2001

# Default slave addresses to probe
DEFAULT_SLAVE_ADDRESSES = [1, 2, 3]


class NicePowerLocator:
    """Scans COM ports for Nice Power supplies (Modbus and D2001) and caches instances."""

    def __init__(self,
                 slave_addresses: List[int] = None,
                 baudrate: int = 9600,
                 timeout: float = 0.3,
                 parity: str = "N",
                 verbose: bool = True):
        """
        :param slave_addresses: List of Modbus slave addresses to probe (default: [1, 2, 3])
        :param baudrate: Serial baudrate (default: 9600)
        :param timeout: Connection timeout in seconds (default: 0.3)
        :param parity: Serial parity 'N' or 'E' (default: 'N')
        :param verbose: Print discovery progress (default: True)
        """
        self.slave_addresses = slave_addresses or DEFAULT_SLAVE_ADDRESSES
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.verbose = verbose
        self._psus: List[Tuple[str, str, int, object]] = []  # [(port, device_type, slave_addr/device_addr, instance)]

    # -------- public API --------
    def refresh(self) -> None:
        """Rescan COM ports, probe for Nice Power supplies (Modbus and D2001)."""
        if self.verbose:
            print(f"[nice_power_locator] Scanning COM ports...")

        # Clear cache
        self._close_all()
        self._psus.clear()

        ports = list_ports.comports()
        if self.verbose:
            print(f"[nice_power_locator] Found {len(ports)} COM port(s)")

        # Probe each port
        for port_info in ports:
            port = port_info.device

            # Skip Bluetooth ports (they can hang)
            if "bluetooth" in port_info.description.lower():
                if self.verbose:
                    print(f"[nice_power_locator] Skipping Bluetooth port: {port} ({port_info.description})")
                continue

            if self.verbose:
                print(f"[nice_power_locator] Probing {port} ({port_info.description})")

            found_on_port = False

            # First, try Modbus (D8001/D6001) with different slave addresses
            for slave_addr in self.slave_addresses:
                try:
                    psu = NicePowerModbus(
                        port=port,
                        slave_addr=slave_addr,
                        baudrate=self.baudrate,
                        timeout=self.timeout,
                        parity=self.parity
                    )

                    # Check if device responds
                    if psu.check_connection():
                        self._psus.append((port, "modbus", slave_addr, psu))
                        if self.verbose:
                            print(f"[nice_power_locator] ✓ Found Modbus PSU at {port}, slave addr {slave_addr}")
                        found_on_port = True
                        break  # Found device at this port, don't try other addresses
                    else:
                        psu.close()

                except Exception as e:
                    if self.verbose:
                        print(f"[nice_power_locator]   Modbus slave {slave_addr}: {type(e).__name__}")
                    try:
                        psu.close()
                    except:
                        pass
                    continue

            # If no Modbus device found, try D2001 custom protocol
            if not found_on_port:
                for device_addr in [0, 1]:  # Try device addresses 0 and 1
                    try:
                        psu = NicePowerD2001(
                            port=port,
                            device_addr=device_addr,
                            baudrate=self.baudrate,
                            timeout=self.timeout
                        )

                        # Check if device responds
                        if psu.check_connection():
                            self._psus.append((port, "d2001", device_addr, psu))
                            if self.verbose:
                                print(f"[nice_power_locator] ✓ Found D2001 PSU at {port}, device addr {device_addr}")
                            found_on_port = True
                            break  # Found device at this port
                        else:
                            psu.close()

                    except Exception as e:
                        if self.verbose:
                            print(f"[nice_power_locator]   D2001 device {device_addr}: {type(e).__name__}")
                        try:
                            psu.close()
                        except:
                            pass
                        continue

        if self.verbose:
            print(f"[nice_power_locator] Discovery complete: {len(self._psus)} Nice Power supply(s)")

    def get_power_supplies(self) -> List[Tuple[str, str, int, object]]:
        """
        Get all discovered Nice Power supplies.
        :return: List of (port, device_type, addr, instance) tuples
                 device_type is "modbus" or "d2001"
                 addr is slave_addr for modbus or device_addr for d2001
        """
        return self._psus.copy()

    def list_found(self) -> List[dict]:
        """Return a friendly summary of discovered devices."""
        result = []
        for port, device_type, addr, psu in self._psus:
            try:
                if device_type == "modbus":
                    vset = psu.read_set_voltage()
                    iset = psu.read_set_current()
                else:  # d2001
                    vset = psu.measure_voltage()
                    iset = psu.measure_current()
                result.append({
                    "port": port,
                    "type": device_type,
                    "addr": addr,
                    "vset": f"{vset:.2f}V",
                    "iset": f"{iset:.2f}A"
                })
            except Exception:
                result.append({
                    "port": port,
                    "type": device_type,
                    "addr": addr,
                    "vset": "N/A",
                    "iset": "N/A"
                })
        return result

    def close_all(self) -> None:
        """Close all connections."""
        self._close_all()
        self._psus.clear()

    # -------- internals --------
    def _close_all(self) -> None:
        """Close all cached PSU connections."""
        for port, device_type, addr, psu in self._psus:
            try:
                psu.close()
            except Exception:
                pass


# ---- Optional CLI demo ----
if __name__ == "__main__":
    loc = NicePowerLocator(verbose=True)
    loc.refresh()

    print("\n== Status ==")
    found = loc.list_found()
    if not found:
        print("No Nice Power supplies found")
    else:
        for info in found:
            print(f"  {info['port']} ({info['type']}, addr {info['addr']}): Vset={info['vset']}, Iset={info['iset']}")

    # Example: use the first PSU if present
    psus = loc.get_power_supplies()
    if psus:
        port, device_type, addr, psu = psus[0]
        print(f"\n[demo] Using first PSU at {port}, type {device_type}, addr {addr}")
        try:
            v_meas = psu.measure_voltage()
            i_meas = psu.measure_current()
            print(f"[demo] Measured: {v_meas:.3f}V, {i_meas:.3f}A")
        except Exception as e:
            print(f"[demo] Measurement failed: {e}")

    # Clean up
    loc.close_all()
