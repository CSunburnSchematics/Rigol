#!/usr/bin/env python3
"""
Serial (Modbus RTU) Nice Power supply locator + initializer.

- Discovers COM/serial ports
- Probes for Nice Power supplies (Modbus slave addresses 1-3)
- Initializes NicePowerSupply instances
- Exposes getters that return ready instances or empty list if none found
"""

from __future__ import annotations
from typing import List, Tuple, Optional
from serial.tools import list_ports
from NICE_POWER_SPPS_D8001_232 import NicePowerSupply

# Default slave addresses to probe
DEFAULT_SLAVE_ADDRESSES = [1, 2, 3]


class NicePowerLocator:
    """Scans COM ports for Nice Power supplies and caches instances."""

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
        self._psus: List[Tuple[str, int, NicePowerSupply]] = []  # [(port, slave_addr, instance)]

    # -------- public API --------
    def refresh(self) -> None:
        """Rescan COM ports, probe for Nice Power supplies."""
        if self.verbose:
            print(f"[nice_power_locator] Scanning COM ports...")

        # Clear cache
        self._close_all()
        self._psus.clear()

        ports = list_ports.comports()
        if self.verbose:
            print(f"[nice_power_locator] Found {len(ports)} COM port(s)")

        # Probe each port with each slave address
        for port_info in ports:
            port = port_info.device
            if self.verbose:
                print(f"[nice_power_locator] Probing {port} ({port_info.description})")

            for slave_addr in self.slave_addresses:
                try:
                    psu = NicePowerSupply(
                        port=port,
                        slave_addr=slave_addr,
                        baudrate=self.baudrate,
                        timeout=self.timeout,
                        parity=self.parity
                    )

                    # Check if device responds
                    if psu.check_connection():
                        self._psus.append((port, slave_addr, psu))
                        if self.verbose:
                            print(f"[nice_power_locator] ✓ Found at {port}, slave addr {slave_addr}")
                        break  # Found device at this port, don't try other addresses
                    else:
                        psu.close()

                except Exception as e:
                    if self.verbose:
                        print(f"[nice_power_locator]   slave {slave_addr}: {type(e).__name__}")
                    try:
                        psu.close()
                    except:
                        pass
                    continue

        if self.verbose:
            print(f"[nice_power_locator] Discovery complete: {len(self._psus)} Nice Power supply(s)")

    def get_power_supplies(self) -> List[Tuple[str, int, NicePowerSupply]]:
        """
        Get all discovered Nice Power supplies.
        :return: List of (port, slave_addr, NicePowerSupply) tuples
        """
        return self._psus.copy()

    def list_found(self) -> List[dict]:
        """Return a friendly summary of discovered devices."""
        result = []
        for port, slave_addr, psu in self._psus:
            try:
                vset = psu.read_set_voltage()
                iset = psu.read_set_current()
                result.append({
                    "port": port,
                    "slave_addr": slave_addr,
                    "vset": f"{vset:.2f}V",
                    "iset": f"{iset:.2f}A"
                })
            except Exception:
                result.append({
                    "port": port,
                    "slave_addr": slave_addr,
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
        for port, slave_addr, psu in self._psus:
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
            print(f"  {info['port']} (slave {info['slave_addr']}): Vset={info['vset']}, Iset={info['iset']}")

    # Example: use the first PSU if present
    psus = loc.get_power_supplies()
    if psus:
        port, slave_addr, psu = psus[0]
        print(f"\n[demo] Using first PSU at {port}, slave {slave_addr}")
        try:
            v_meas = psu.measure_voltage()
            i_meas = psu.measure_current()
            print(f"[demo] Measured: {v_meas:.3f}V, {i_meas:.3f}A")
        except Exception as e:
            print(f"[demo] Measurement failed: {e}")

    # Clean up
    loc.close_all()
