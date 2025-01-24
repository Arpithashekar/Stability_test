import sys
import time
import subprocess
import os
import logging
import random
from logging.handlers import RotatingFileHandler
from datetime import datetime
base_path = os.path.abspath('C:\\RobotTest\\projects\\Reception-Test-Scripts\\gfw\\giftdroid')
sys.path.append(base_path)
from scripts.lib.bits_platform import bits_platform
from tuner_operation import tuner_operation
from scripts.lib.sinkpadprobe.sinkpadprob_values import sinkpadprob_values


class GiftdroidPowertower:
    def __init__(self, sink_file_path, audio_validation_type=None):
        self.directory_path = None
        self.log_file = None
        self.filename = None
        self.audio_l = None
        self.audio_r = None
        self.mute_start_time = None
        self.timer_started = False
        self.timer_start_time = None
        self.total_mute_time = 0
        self.count = 0
        self.sbr_service = "sbr_pid_name"
        self.brhal_service = "brhal_pid_name"
                # Initialize BITS tool and relays
        self.bits_tool = bits_platform()
        # Assign parameters to class attributes
        self.sink_file_path = "C:\\RobotTest\\Projects\\Reception-Test-Scripts\\gfw\\giftdroid\\scripts\\lib\\sinkpadprobe\\sink.txt"
        self.sinkpadprob_values_instance = sinkpadprob_values(sink_file_path = self.sink_file_path)
        self.tuner_operation_instance = tuner_operation(audio_validation_type="sinkpadprob", sink_file_path=self.sink_file_path)

    def creating_directory(self):
        # Creating directory with the current date and time
        current_date = datetime.now().strftime('%Y-%m-%d-%H-%M')
        self.directory_path = os.path.join("D:/CCS2/Ignition_cycle/logs/", current_date)

        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
            print(f"Directory '{current_date}' created successfully at {self.directory_path}")

        # Setting up logging after directory is created
        self.setup_logging()

    def setup_logging(self):
        # To capture script logs
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Log file rotation in the newly created directory
        file_handler = RotatingFileHandler(f'{self.directory_path}/script_log.txt', backupCount=5)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
        logging.getLogger().addHandler(file_handler)

        # Initialize custom log file for other logs
        self.log_file = open(os.path.join(self.directory_path, 'custom_log.txt'), 'a')

    def soc_version(self):
        try:
            result = subprocess.run(['adb', 'shell', 'getprop', 'ro.build.internal.id'], capture_output=True, text=True, check=True)
            SOC_VERSION = result.stdout.strip()
            logging.info(f"SOC_VERSION: {SOC_VERSION}")
            if self.log_file:
                self.log_file.write(f"SOC_VERSION: {SOC_VERSION}\n")
        except subprocess.CalledProcessError:
            logging.error("Failed to get SOC version")

    def sbr_version(self):
        try:
            result = subprocess.run(['adb', 'shell', 'cat /vendor/etc/reg/ars_version.txt'], capture_output=True, text=True, check=True)
            version_line = [line for line in result.stdout.split('\n') if 'Version:' in line]
            if version_line:
                SBR_VERSION = version_line[0].split('Version:')[1].strip()
                logging.info(f"SBR_VERSION: {SBR_VERSION}")
                if self.log_file:
                    self.log_file.write(f"SBR_VERSION: {SBR_VERSION}\n")
            else:
                logging.error("Version information not found in output.")
        except subprocess.CalledProcessError as e:
            logging.error(f"adb shell command failed: {e}")

    def adb_traces(self, count):
        try:
            exc_cmd = f"adb logcat > {self.directory_path}/log_file{self.count}.txt"
            self.filename=f"log_file{self.count}.txt"
            subprocess.Popen(exc_cmd, shell=True)
            logging.info(f"Logs are being created at {self.directory_path}")
        except subprocess.CalledProcessError as e:
            logging.error("Error: Command returned non-zero exit status", e.returncode)
        except Exception as e:
            logging.error(f"Error: {e}")

        # Turning on IGN & ACC after 3 minutes
    def cold_start(self):
        random_start_time = [180, 200, 210, 230]
        random_time_ign_on = random.choice(random_start_time)
        logging.info(f"\nShutdown will be cancelled after {random_time_ign_on}\n")
        self.log_file.write(f"\nShutdown will be cancelled after {random_time_ign_on}\n")
        self.bits_tool.output_switch_relay(1, 2, 'OFF')
        time.sleep(10)
        self.bits_tool.output_switch_relay(1, 2, 'ON')

    def enabling_adb_logs(self):
        """Enable specific ADB logging for the SBR and BRHAL services."""
        adb_cmds = [
            "adb shell setprop persist.log.tag.BRHAL DEBUG",
            "adb shell setprop persist.log.tag.rbs DEBUG",
            "adb shell setprop persist.log.tag.rbs VERBOSE",
            "adb shell setprop persist.log.tag.BRHAL VERBOSE",
            "adb shell setprop persist.log.tag.BRHAL V",
            "adb shell setprop persist.log.tag.ars INFO",
            "adb shell sync"
        ]
        try:
            for adb_cmd in adb_cmds:
                subprocess.run(adb_cmd, shell=True, check=True)
            logging.info("Logs have been enabled for SBR, BRHAL, and Audio services.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to enable ADB logs: {e}")

    def restart(self):
        """Restart the target by controlling the relay switches."""
        try:
            self.bits_tool.output_switch_relay(1, 1, 'OFF')
            self.bits_tool.output_switch_relay(1, 2, 'OFF')
            logging.info("Turning off the target for restart...")
            time.sleep(10)
            self.bits_tool.output_switch_relay(1, 1, 'ON')
            self.bits_tool.output_switch_relay(1, 2, 'ON')
            logging.info("Target has been restarted.")
        except Exception as e:
            logging.error(f"Failed to restart the target: {e}")

    def adb_root(self):
        """Attempt to set the device to root mode with retries."""
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            result = subprocess.run(['adb', 'root'], capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("Device set to root mode successfully.")
                break
            retry_count += 1
            logging.warning(f"Retrying ADB root ({retry_count}/{max_retries})...")
            time.sleep(10)

            if retry_count == max_retries:
                logging.error("Max retries reached for ADB root. Restarting the target.")
                self.restart()
                retry_count = 0  # Reset counter after restart attempt
        
        adb_cmds = [
        "adb root",
        "adb shell umount -l /system_ext",
        "adb shell umount -l /vendor/etc",
        "adb remount"]
        for adb_cmd in adb_cmds:
                subprocess.run(adb_cmd, shell=True, check=True)

    def service_pid(self, service):
        try:
            result = subprocess.run(['adb', 'shell', 'pidof', service], capture_output=True, text=True, check=True)
            pid = result.stdout.strip()
            if pid.isdigit():
                logging.info(f"PID for {service}: {pid}")
                return int(pid)
            else:
                logging.error(f"No PID found for service: {service}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get PID for service {service}: {e}")
        return None

    def test_monitor_sbrpid(self, service):
        """Monitor the PID of the SBR service and log reset events."""
        current_pid = self.service_pid(service)
        if self.previous_sbrpid == current_pid or self.previous_sbrpid is None:
            logging.debug(f"No PID change for {service}. Current PID: {current_pid}")
        else:
            logging.info(f"PID changed for {service}: from {self.previous_sbrpid} to {current_pid}")
            # Log to issue file
            with open(os.path.join(self.directory_path, 'Issue_file.txt'), 'a') as issue:
                issue.write(f"{self.filename}: sbr_reset\n")
            self.log_file.write(f"PID changed for {service}: from {self.previous_sbrpid} to {current_pid}")
            self.previous_sbrpid = current_pid


    def test_monitor_brhalpid(self, service):
        """Monitor the PID of the BRHAL service and log reset events."""
        current_pid = self.service_pid(service)
        if self.previous_brhalpid is None or current_pid != self.previous_brhalpid:
            logging.info(f"PID changed for {service}: from {self.previous_brhalpid} to {current_pid}")
            # Log to issue file
            with open(os.path.join(self.directory_path, 'Issue_file.txt'), 'a') as issue:
                issue.write(f"{self.filename}: brhal_reset\n")
            self.log_file.write(f"PID changed for {service}: from {self.previous_brhalpid} to {current_pid}")
            self.previous_brhalpid = current_pid
        else:
            logging.debug(f"No PID change for {service}. Current PID: {current_pid}")

    def kill_logcat(self):
        """Kill the logcat process if it is running."""
        command = "adb shell \"kill -9 $(ps -ef | grep '[l]ogcat' | awk '{print $2}')\""
        try:
            subprocess.run(command, shell=True, check=True)
            logging.info("Logcat process terminated successfully.")
        except subprocess.CalledProcessError:
            logging.warning("No active logcat process found or failed to kill logcat.")

    def clear_tombstone_files(self):
        """Clear all tombstone files from the device."""
        try:
            subprocess.run(['adb', 'shell', 'rm', '-rf', '/data/tombstones/*'], check=True)
            logging.info("Tombstone files cleared successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to clear tombstone files: {e}")

    def get_number_of_tombstone_files(self):
        """Retrieve the count of tombstone files on the device."""
        try:
            result = subprocess.run(['adb', 'shell', 'ls', '/data/tombstones'], capture_output=True, text=True, check=True)
            file_list = result.stdout.strip().split('\n')
            num_files = len(file_list) if file_list[0] else 0
            logging.info(f"Number of tombstone files: {num_files}")
            with open(os.path.join(self.directory_path, 'Issue_file.txt'), 'a') as issue:
                issue.write(f"Number of tombstone files: {num_files}")
            return num_files
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to retrieve tombstone files: {e}")
            return 0

    def reset_in_tombstones(self):
        """Identify reset reasons in tombstone files and log them."""
        try:
            reset_reasons = []
            num_files = self.get_number_of_tombstone_files()

            for i in range(num_files):
                filename = f"tombstone_{i:02d}"
                result = subprocess.run(['adb', 'shell', 'cat', f'/data/tombstones/{filename}'], capture_output=True, text=True, check=True)
                cmd_lines = [line for line in result.stdout.split('\n') if 'Cmdline:' in line]

                if cmd_lines:
                    reset_reason = cmd_lines[0].split('Cmdline:')[1].strip()
                    logging.info(f"Reset reason in {filename}: {reset_reason}")
                    with open(os.path.join(self.directory_path, 'Issue_file.txt'), 'a') as issue:
                        issue.write(f"Reset reason in {filename}: {reset_reason}")
                    if self.log_file:
                        self.log_file.write(f"Reset reason in {filename}: {reset_reason}\n")

                    reset_reasons.append(reset_reason)
                else:
                    logging.warning(f"No Cmdline info in {filename}.")
            return reset_reasons
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to retrieve reset reasons: {e}")
            return []


    def audio_validation_sinkpad(self):
        self.sinkpadprob_values_instance.get_sink_file()
        self.audio_l = self.sinkpadprob_values_instance.get_audio_l_value()
        self.audio_r = self.sinkpadprob_values_instance.get_audio_r_value()
        if self.audio_l == 0 or self.audio_r == 0:
            print(f"no audio")
            if self.mute_start_time is None:
                self.mute_start_time = time.time()

            if not self.timer_started:
                self.timer_started = True
                self.timer_start_time = time.time()

        else:
            if self.mute_start_time is not None:
                self.mute_duration = time.time() - self.mute_start_time
                self.total_mute_time += self.mute_duration
                logging.info(f"Mute lasted for {self.mute_duration} seconds")
                with open(os.path.join(self.directory_path, 'Issue_file.txt'), 'a') as issue:
                    issue.write(f"{self.filename}: mute for {self.mute_duration} seconds\n")
                self.mute_start_time = None

            if self.timer_started:
                self.timer_started = False



    def checking_for_issues(self):
        """Perform various checks to monitor SBR resets, BRHAL resets, and long audio mute."""
        result = False

        # Open the issue file to log resets during the checks
        with open(os.path.join(self.directory_path, 'Issue_file.txt'), 'a') as issue:
            try:
                logging.info("Loading file and monitoring for issues...")
                self.filepath = os.path.join(self.directory_path, f"log_file{self.count}.txt")
                self.previous_sbrpid = None
                self.previous_brhalpid = None
                self.current_sbrpid = None
                self.current_brhalpid = None
                self.cold_start()
                time.sleep(30)
                self.adb_root()
                self.enabling_adb_logs()
                self.adb_traces(self.count)
                cold_start_interval = 5*60
                start_time = time.time()
                while time.time() - start_time < cold_start_interval:
                    self.test_monitor_sbrpid(self.sbr_service)  # Check for SBR PID changes
                    self.test_monitor_brhalpid(self.brhal_service)  # Check for BRHAL PID changes
                    self.audio_validation_sinkpad()
                    
            except UnicodeDecodeError as e:
                logging.error(f"Unicode error while reading log file: {e}")

        return result


    def run_test_cycles(self, duration_days):
        # Ensure directory and logging setup
        self.creating_directory()

        # Paths for log files used in the test cycles
        log_filepath = os.path.join(self.directory_path, "dump_file.txt")
        issue_filepath = os.path.join(self.directory_path, "Issue_file.txt")


        self.bits_tool.output_switch_relay(1, 1, 'ON')  # Battery connected to relay 1
        self.bits_tool.output_switch_relay(1, 2, 'ON')  # Ignition connected to relay 2
        logging.info('Battery and Ignition connected to relays.')
        self.adb_root()
        self.soc_version()
        self.sbr_version()
        self.clear_tombstone_files()
        start_time_script = time.time()
        end_time_script = start_time_script +12*60*60  # Set timeout in seconds
        self.tuner_operation_instance.enable_sinkpad_probe()
        
        while time.time() < end_time_script:
            self.count += 1
            logging.info(f"Checking for issues in cycle number {self.count}")
            result = self.checking_for_issues()
            if result:
                logging.info(f"Issue found in cycle {self.count}")
                # Additional handling if issues are found

            time.sleep(10)  # Simulate delay between cycles

        # Final logging and cleanup
        self.reset_in_tombstones()
        logging.getLogger().handlers.clear()

    # Make sure to close log_file when the class instance is no longer used
    def __del__(self):
        if self.log_file:
            self.log_file.close()

def main():
    sink_file_path = 'C:\\RobotTest\\Projects\\Reception-Test-Scripts\\gfw\\giftdroid\\scripts\\lib\\sinkpadprobe\\sink.txt'
    
    # Create an instance of GiftdroidPowertower
    giftdroid_instance = GiftdroidPowertower(sink_file_path=sink_file_path)

    # Call the method with parentheses
    giftdroid_instance.run_test_cycles(duration_days=1)
    
    # Uncomment this if `enable_sinkpad_probe` is a method you need
    # giftdroid_instance.tuner_operation_instance.enable_sinkpad_probe() 

if __name__ == "__main__":
    main()
