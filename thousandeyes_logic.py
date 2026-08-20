import os
import time
import json
import requests
import threading
from datetime import datetime
from logger import Logger
from log_rotator import LogRotator
from config_loader import config


class ThousandEyesLogic:
    """ThousandEyes instant-test API client with SNMP/Kafka metrics collection."""

    AVAILABLE_TESTS = {
        "http_get_mt": "Downstream (HTTP GET Multi-Thread)",
        "http_post_mt": "Upstream (HTTP POST Multi-Thread)",
        "udp_jitter": "UDP Jitter / Latency",
    }

    def __init__(self, scenario_name, test_group_name=None, rtt_suffix="", unit_id=None):
        self.logger = Logger("ThousandEyesLogic")
        self.scenario_name = scenario_name
        self.test_group_name = test_group_name
        self.rtt_suffix = rtt_suffix
        self.test_id = int(datetime.now().timestamp())
        self.timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        # API config
        self.api_url = config.thousandeyes_api_url
        self.api_token = config.thousandeyes_api_token
        self.unit_id = unit_id  # required CLI argument
        self.app_name = config.thousandeyes_app_name
        self.timeout = config.thousandeyes_timeout

        if not self.unit_id:
            raise ValueError("ThousandEyes unit_id is required (pass --unit-id on CLI)")

        # Output naming
        if self.test_group_name:
            self.output_prefix = f"{self.test_group_name}_ThousandEyes_{self.timestamp_str}"
        else:
            self.output_prefix = f"ThousandEyes_{self.timestamp_str}"

        self.log_file = os.path.join(os.getcwd(), "logs", f"thousandeyes_{self.test_id}.log")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self.log_rotator = LogRotator(self.log_file)

        # All tests run every time (DS throughput, US throughput, jitter/latency)
        self.test_sequence = ["http_get_mt", "http_post_mt", "udp_jitter"]

        # Per-iteration result storage (populated by run_downstream/run_upstream)
        self._last_ds_result = None
        self._last_us_result = None

    def _build_url(self):
        return f"{self.api_url}/units/{self.unit_id}/tests"

    def _run_test(self, test_name, result_store=None):
        """Execute a single ThousandEyes instant test via API.

        If result_store dict is provided, stores result under test_name key
        (used for concurrent execution via threads).
        Returns (data, elapsed_s) tuple.
        """
        url = self._build_url()
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        payload = json.dumps({"test": test_name, "appName": self.app_name})

        self.logger.info(f"Running ThousandEyes test: {test_name} on unit {self.unit_id} (waiting for result...)")
        print(f"\n  [{test_name}] Executing on unit {self.unit_id} — waiting for completion...", flush=True)
        start_time = time.time()

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=self.timeout)
            elapsed = time.time() - start_time
            response.raise_for_status()
            result = response.json()

            log_content = f"\n=== ThousandEyes {test_name} ===\n"
            log_content += f"URL: {url}\n"
            log_content += f"Status: {response.status_code}\n"
            log_content += f"Elapsed: {elapsed:.1f}s\n"
            log_content += f"Response: {json.dumps(result, indent=2)}\n"
            self.log_rotator.write_log(log_content)

            if result.get("code") == "OK" and result.get("data", {}).get("success"):
                data = result["data"]
                print(f"  [{test_name}] Completed in {elapsed:.1f}s", flush=True)
                self._print_result(test_name, data)
                if result_store is not None:
                    result_store[test_name] = data
                return data, elapsed
            else:
                self.logger.error(f"ThousandEyes test failed: {result.get('message', 'Unknown error')}")
                return None, elapsed

        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            self.logger.error(f"ThousandEyes API timeout after {elapsed:.0f}s (limit: {self.timeout}s)")
            self.log_rotator.write_log(f"\nERROR: API timeout for {test_name} after {elapsed:.0f}s\n")
            return None, elapsed
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            self.logger.error(f"ThousandEyes API error: {e}")
            self.log_rotator.write_log(f"\nERROR: {e}\n")
            return None, elapsed

    def _run_tests_concurrent(self, test_names):
        """Run multiple tests simultaneously in threads so timestamps align."""
        results = {}
        threads = [
            threading.Thread(target=self._run_test, args=(name, results), daemon=True)
            for name in test_names
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=self.timeout + 30)
        return results

    def _print_result(self, test_name, data):
        """Display test result summary."""
        print(f"\n  ThousandEyes {test_name}:")
        print(f"    Unit: {data.get('unit_id')} | MAC: {data.get('mac')}")
        print(f"    Target: {data.get('target')}")
        print(f"    Time: {data.get('utc_datetime')}")

        if test_name in ("http_get_mt", "http_post_mt"):
            bps = data.get("bytes_sec", 0)
            mbps = (bps * 8) / 1_000_000
            direction = "Download" if test_name == "http_get_mt" else "Upload"
            print(f"    {direction}: {mbps:.2f} Mbps ({bps:,} bytes/sec)")
        elif test_name == "udp_jitter":
            print(f"    Latency: {data.get('latency', 0)} µs")
            print(f"    Down Jitter: {data.get('down_jitter', 0)} µs")
            print(f"    Up Jitter: {data.get('up_jitter', 0)} µs")

    def _get_output_dir(self, iteration, total_iterations, parent_output_dir):
        """Determine output directory for this iteration."""
        if parent_output_dir:
            if total_iterations > 1:
                output_dir = os.path.join(parent_output_dir, f"iteration_{iteration + 1}")
            else:
                output_dir = parent_output_dir
        else:
            if total_iterations > 1:
                output_dir = os.path.join("Results", self.output_prefix, f"iteration_{iteration + 1}")
            else:
                output_dir = os.path.join("Results", self.output_prefix)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def run_downstream(self, iteration, total_iterations, parent_output_dir=None):
        """Run downstream test only (http_get_mt). Returns (success, elapsed_s)."""
        self.logger.info(f"Iteration {iteration + 1}/{total_iterations} - ThousandEyes DS (http_get_mt)")
        data, elapsed = self._run_test("http_get_mt")
        if data:
            self._last_ds_result = data
            self._last_ds_elapsed = elapsed
            return True, elapsed
        return False, elapsed

    def run_upstream(self, iteration, total_iterations, parent_output_dir=None):
        """Run upstream test only (http_post_mt). Returns (success, elapsed_s)."""
        self.logger.info(f"Iteration {iteration + 1}/{total_iterations} - ThousandEyes US (http_post_mt)")
        data, elapsed = self._run_test("http_post_mt")
        if data:
            self._last_us_result = data
            self._last_us_elapsed = elapsed
            return True, elapsed
        return False, elapsed

    def run_jitter(self, iteration, total_iterations, parent_output_dir=None):
        """Run jitter/latency test only (udp_jitter) and save all results."""
        self.logger.info(f"Iteration {iteration + 1}/{total_iterations} - ThousandEyes Jitter (udp_jitter)")
        output_dir = self._get_output_dir(iteration, total_iterations, parent_output_dir)
        data, elapsed = self._run_test("udp_jitter")

        # Collect all results from this iteration
        results = {}
        if self._last_ds_result:
            results["http_get_mt"] = self._last_ds_result
        if self._last_us_result:
            results["http_post_mt"] = self._last_us_result
        if data:
            results["udp_jitter"] = data

        self._save_results(output_dir, iteration, results)

        # Clear stored results for next iteration
        self._last_ds_result = None
        self._last_us_result = None

        return data is not None

    def run_scenario(self, iteration, total_iterations, parent_output_dir=None):
        """Run all 3 ThousandEyes tests sequentially with a short gap between each."""
        self.logger.info(f"Iteration {iteration + 1}/{total_iterations} - ThousandEyes{self.rtt_suffix}")

        output_dir = self._get_output_dir(iteration, total_iterations, parent_output_dir)

        results = {}
        all_passed = True
        for test_name in self.test_sequence:
            data, _ = self._run_test(test_name)
            if data:
                results[test_name] = data
            else:
                all_passed = False

        self._save_results(output_dir, iteration, results)

        if all_passed:
            self.logger.info(f"✓ Iteration {iteration + 1} completed - {len(results)}/3 tests passed")
        else:
            self.logger.error(f"✗ Iteration {iteration + 1} - {len(results)}/3 tests passed")

        if iteration < total_iterations - 1:
            time.sleep(10)

        return all_passed

    def _save_results(self, output_dir, iteration, results):
        """Save test results to JSON and text report with raw values and conversions."""
        if not results:
            return

        base_name = f"ThousandEyes_{self.test_group_name or 'test'}_iteration_{iteration + 1}"

        # --- JSON output (machine-readable) ---
        json_file = os.path.join(output_dir, f"{base_name}.json")
        output = {
            "test_group": self.test_group_name,
            "unit_id": self.unit_id,
            "iteration": iteration + 1,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": self._build_summary(results),
        }
        with open(json_file, "w") as f:
            json.dump(output, f, indent=2)
        self.logger.info(f"JSON saved: {os.path.basename(json_file)}")

        # --- Text report (human-readable with raw values + conversions) ---
        txt_file = os.path.join(output_dir, f"{base_name}.txt")
        self._write_text_report(txt_file, results, iteration)
        self.logger.info(f"Report saved: {os.path.basename(txt_file)}")

    def _build_summary(self, results):
        """Build summary dict with raw values and unit conversions."""
        summary = {}
        for test_name, data in results.items():
            if test_name in ("http_get_mt", "http_post_mt"):
                bytes_sec = data.get("bytes_sec", 0)
                summary[test_name] = {
                    "raw_bytes_sec": bytes_sec,
                    "mbps": round((bytes_sec * 8) / 1_000_000, 4),
                    "gbps": round((bytes_sec * 8) / 1_000_000_000, 6),
                    "MBps": round(bytes_sec / 1_000_000, 4),
                }
            elif test_name == "udp_jitter":
                latency_us = data.get("latency", 0)
                down_jitter_us = data.get("down_jitter", 0)
                up_jitter_us = data.get("up_jitter", 0)
                summary[test_name] = {
                    "raw_latency_us": latency_us,
                    "latency_ms": round(latency_us / 1000, 4),
                    "raw_down_jitter_us": down_jitter_us,
                    "down_jitter_ms": round(down_jitter_us / 1000, 4),
                    "raw_up_jitter_us": up_jitter_us,
                    "up_jitter_ms": round(up_jitter_us / 1000, 4),
                }
        return summary

    def _write_text_report(self, filepath, results, iteration):
        """Write formatted text report with raw values and conversions."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  THOUSANDEYES INSTANT TEST REPORT")
        lines.append("=" * 70)
        lines.append(f"  Test Group:  {self.test_group_name or 'N/A'}")
        lines.append(f"  Unit ID:     {self.unit_id}")
        lines.append(f"  Iteration:   {iteration + 1}")
        lines.append(f"  Timestamp:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # --- Downstream Throughput ---
        ds = results.get("http_get_mt")
        if ds:
            bytes_sec = ds.get("bytes_sec", 0)
            lines.append("")
            lines.append("-" * 70)
            lines.append("  DOWNSTREAM THROUGHPUT (http_get_mt)")
            lines.append("-" * 70)
            lines.append(f"  Target:          {ds.get('target')}")
            lines.append(f"  MAC:             {ds.get('mac')}")
            lines.append(f"  UTC Time:        {ds.get('utc_datetime')}")
            lines.append(f"")
            lines.append(f"  Raw Value:       {bytes_sec:,} bytes/sec")
            lines.append(f"  Conversion:      {bytes_sec} × 8 / 1,000,000 = {(bytes_sec * 8) / 1_000_000:.4f} Mbps")
            lines.append(f"")
            lines.append(f"  Result:          {(bytes_sec * 8) / 1_000_000:.2f} Mbps")
            lines.append(f"                   {(bytes_sec * 8) / 1_000_000_000:.4f} Gbps")
            lines.append(f"                   {bytes_sec / 1_000_000:.2f} MB/s")

        # --- Upstream Throughput ---
        us = results.get("http_post_mt")
        if us:
            bytes_sec = us.get("bytes_sec", 0)
            lines.append("")
            lines.append("-" * 70)
            lines.append("  UPSTREAM THROUGHPUT (http_post_mt)")
            lines.append("-" * 70)
            lines.append(f"  Target:          {us.get('target')}")
            lines.append(f"  MAC:             {us.get('mac')}")
            lines.append(f"  UTC Time:        {us.get('utc_datetime')}")
            lines.append(f"")
            lines.append(f"  Raw Value:       {bytes_sec:,} bytes/sec")
            lines.append(f"  Conversion:      {bytes_sec} × 8 / 1,000,000 = {(bytes_sec * 8) / 1_000_000:.4f} Mbps")
            lines.append(f"")
            lines.append(f"  Result:          {(bytes_sec * 8) / 1_000_000:.2f} Mbps")
            lines.append(f"                   {(bytes_sec * 8) / 1_000_000_000:.4f} Gbps")
            lines.append(f"                   {bytes_sec / 1_000_000:.2f} MB/s")

        # --- UDP Jitter / Latency ---
        jitter = results.get("udp_jitter")
        if jitter:
            latency_us = jitter.get("latency", 0)
            down_jitter_us = jitter.get("down_jitter", 0)
            up_jitter_us = jitter.get("up_jitter", 0)
            lines.append("")
            lines.append("-" * 70)
            lines.append("  UDP JITTER / LATENCY (udp_jitter)")
            lines.append("-" * 70)
            lines.append(f"  Target:          {jitter.get('target')}")
            lines.append(f"  MAC:             {jitter.get('mac')}")
            lines.append(f"  UTC Time:        {jitter.get('utc_datetime')}")
            lines.append(f"")
            lines.append(f"  Latency:")
            lines.append(f"    Raw Value:     {latency_us} µs")
            lines.append(f"    Conversion:    {latency_us} / 1000 = {latency_us / 1000:.4f} ms")
            lines.append(f"    Result:        {latency_us / 1000:.3f} ms")
            lines.append(f"")
            lines.append(f"  Down Jitter:")
            lines.append(f"    Raw Value:     {down_jitter_us} µs")
            lines.append(f"    Conversion:    {down_jitter_us} / 1000 = {down_jitter_us / 1000:.4f} ms")
            lines.append(f"    Result:        {down_jitter_us / 1000:.3f} ms")
            lines.append(f"")
            lines.append(f"  Up Jitter:")
            lines.append(f"    Raw Value:     {up_jitter_us} µs")
            lines.append(f"    Conversion:    {up_jitter_us} / 1000 = {up_jitter_us / 1000:.4f} ms")
            lines.append(f"    Result:        {up_jitter_us / 1000:.3f} ms")

        # --- Summary Table ---
        lines.append("")
        lines.append("=" * 70)
        lines.append("  SUMMARY")
        lines.append("=" * 70)
        lines.append(f"  {'Metric':<30} {'Raw Value':<20} {'Converted':<20}")
        lines.append(f"  {'-'*30} {'-'*20} {'-'*20}")
        if ds:
            lines.append(f"  {'DS Throughput (TCP)':<30} {ds.get('bytes_sec', 0):>14} B/s  {(ds.get('bytes_sec', 0) * 8) / 1_000_000:>12.2f} Mbps")
        if us:
            lines.append(f"  {'US Throughput (TCP)':<30} {us.get('bytes_sec', 0):>14} B/s  {(us.get('bytes_sec', 0) * 8) / 1_000_000:>12.2f} Mbps")
        if jitter:
            lines.append(f"  {'Latency':<30} {jitter.get('latency', 0):>14} µs   {jitter.get('latency', 0) / 1000:>12.3f} ms")
            lines.append(f"  {'Down Jitter':<30} {jitter.get('down_jitter', 0):>14} µs   {jitter.get('down_jitter', 0) / 1000:>12.3f} ms")
            lines.append(f"  {'Up Jitter':<30} {jitter.get('up_jitter', 0):>14} µs   {jitter.get('up_jitter', 0) / 1000:>12.3f} ms")
        lines.append("=" * 70)
        lines.append("")

        with open(filepath, "w") as f:
            f.write("\n".join(lines))

        # Also print summary to terminal
        print(f"\n  {'='*60}")
        print(f"  THOUSANDEYES SUMMARY \u2014 Iteration {iteration + 1}")
        print(f"  {'='*60}")
        if ds:
            print(f"  DS Throughput (TCP): {(ds.get('bytes_sec', 0) * 8) / 1_000_000:.2f} Mbps  (raw: {ds.get('bytes_sec', 0):,} bytes/sec)")
        if us:
            print(f"  US Throughput (TCP): {(us.get('bytes_sec', 0) * 8) / 1_000_000:.2f} Mbps  (raw: {us.get('bytes_sec', 0):,} bytes/sec)")
        if jitter:
            print(f"  Latency:        {jitter.get('latency', 0) / 1000:.3f} ms    (raw: {jitter.get('latency', 0)} µs)")
            print(f"  Down Jitter:    {jitter.get('down_jitter', 0) / 1000:.3f} ms    (raw: {jitter.get('down_jitter', 0)} µs)")
            print(f"  Up Jitter:      {jitter.get('up_jitter', 0) / 1000:.3f} ms    (raw: {jitter.get('up_jitter', 0)} µs)")
        print(f"  {'='*60}\n", flush=True)

    def run_iterations(self, count=1, parent_output_dir=None):
        """Run multiple ThousandEyes iterations (all 3 tests per iteration)."""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ThousandEyes: http_get_mt + http_post_mt + udp_jitter")
        self.logger.info(f"Unit ID: {self.unit_id}")
        self.logger.info(f"Iterations: {count}")
        self.logger.info(f"{'='*60}")

        success_count = 0

        for i in range(count):
            if self.run_scenario(i, count, parent_output_dir):
                success_count += 1
            else:
                self.logger.error(f"✗ Iteration {i + 1} failed")

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ThousandEyes completed: {success_count}/{count} iterations successful")
        self.logger.info(f"{'='*60}\n")
        return success_count == count
