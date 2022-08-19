import asyncio, asyncssh, sys
import time
import threading
import socket, errno
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

class OpenSSH:
    def __init__(self, host, username, password, port, known_hosts = None):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.known_hosts = known_hosts
        self.conn = None
        self.ssh_status = None

    async def run_client(self, stop):
        async with asyncssh.connect(
            host = self.host,
            username = self.username,
            password = self.password,
            port = 22,
            known_hosts = self.known_hosts
        ) as conn:
            listener = await conn.forward_socks('127.0.0.1', self.port)
            self.ssh_status = True
            while not stop():
                await asyncio.sleep(0.1)

    def thr(self, stop):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_client(stop))
        except (OSError, asyncssh.Error) as exc:
            self.ssh_status = False
            loop.close()
            print('SSH connection failed: ' + str(exc))

    def waitResult(self):
        while self.ssh_status == None:
            time.sleep(0.1)
        return self.ssh_status

class SSHProxyControler:
    def __init__(self, host, username, password, port, known_hosts = None, port_retry = 100, stop_thread = False):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.known_hosts = known_hosts
        self.stop_thread = stop_thread
        self.port_retry = port_retry

    def start(self):
        while True:
            if self.port_retry != 0:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.bind(("127.0.0.1", self.port))
                except socket.error as e:
                    if e.errno == errno.EADDRINUSE:
                        self.port += 1
                        self.port_retry -= 1
                    else:
                        return False, self.host, self.port
                s.close()
                break
            else:
                return False, self.host, self.port
    
        myssh = OpenSSH(self.host, self.username, self.password, self.port)
        t1 = threading.Thread(target = myssh.thr, args=(lambda: self.stop_thread, ))
        t1.daemon = True
        t1.start()
        return myssh.waitResult(), self.host, self.port
  
    def stop(self):
        self.stop_thread = True

if __name__ == '__main__':
    controlssh = SSHProxyControler('172.16.0.100', 'root', 'TestForwarder', 1080)
    sshstatus, host, port = controlssh.start()
    print(sshstatus, host, port)
    if sshstatus:
        userAgent = UserAgent().safari
        print(userAgent)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1024,768')
        chrome_options.add_argument(f'user-agent={userAgent}')
        chrome_options.add_argument("--proxy-server=socks5://127.0.0.1:1080")
        driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(),chrome_options=chrome_options)
        driver.implicitly_wait(30)
        actions = webdriver.ActionChains(driver)
        driver.get("https://www.google.com/")
        print (driver.page_source)
        driver.quit()
        controlssh.stop()
        print('SSH is Stoped')
    else:
        print('Can not connect to SSH')
