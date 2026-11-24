"""Settings > Balance Guides: how to set up, calibrate and troubleshoot each brand of balance.

The text comes from the manuals in the archive (``Ignore/Balance Brands/``: Lachoi JT-D, Ohaus
Adventurer AR, MyWeigh iBalance i211) and, for Bonvoisin, from the menu guide Brandon found.
Each guide's title is the brand's name in a balance tab's Brand box, so a tab can open its own
guide with ``SettingsTab.show_guide(brand)``.
"""

from PyQt6.QtWidgets import QTabWidget, QTextBrowser, QVBoxLayout, QWidget

# The serial settings every balance needs, because the app always opens the port this way.
_PORT = "<b>9600 baud, 8 data bits, no parity, 1 stop bit</b>, no handshake"

_STYLE = """
h2 { color: #3498db; }
h3 { color: #3498db; margin-top: 14px; }
td, th { padding: 4px 8px; vertical-align: top; }
th { text-align: left; }
.note { color: #e67e22; }
"""


def _table(header, rows):
    head = "".join(f"<th>{h}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table border='1' cellspacing='0'><tr>{head}</tr>{body}</table>"


COMMON = f"""
<h2>Start here: common problems</h2>
<p>Every balance must be set to {_PORT}. In each balance tab, pick the matching <b>Brand</b>,
choose the port, then press <b>Connect</b>. The tab for each brand has its own guide.</p>
<p>Not sure which brand it is, or whether it's set right? Choose the port and press <b>Detect</b>
next to the Brand box. It listens first and then only asks for a reading (never tare or
calibration), and it says if the balance is set to another speed than 9600 baud.</p>

<h3>The balance's port isn't in the list</h3>
<ul>
<li>Plug in the USB-to-serial cable, then press <b>Refresh Ports</b>.</li>
<li>Windows: the port shows as <code>COM3</code>, <code>COM12</code>, ... In Device Manager it is
under <i>Ports (COM &amp; LPT)</i>. A yellow warning sign there means the cable's driver is missing
(usually Prolific PL2303, WCH CH340 or FTDI; the name is on the cable or its box).</li>
<li>Mac: the port looks like <code>/dev/cu.usbserial-...</code>. Ignore
<code>/dev/cu.debug-console</code> and the Bluetooth ports, which are never a balance.</li>
<li>Try another USB socket, or the cable without a hub.</li>
</ul>

<h3>"COM12 isn't on this computer"</h3>
<p>The tab was last connected on another computer. Choose this computer's port for the balance
and press Connect: each computer remembers its own port from then on.</p>

<h3>"... is already in use by the tab ..."</h3>
<p>Another tab is connected to that port. Each balance needs its own cable and port: disconnect
the other tab, or pick the right port for this one.</p>

<h3>"Connection Failed" / "Could not connect"</h3>
<ul>
<li><i>Access is denied</i>, <i>Resource busy</i> or <i>Permission denied</i>: another program
has the port open (another copy of a balance program, a serial terminal, the balance's own
software). Close it, or unplug and re-plug the cable.</li>
<li><i>File not found</i> / <i>could not open port</i>: the cable was unplugged. Press
Refresh Ports and choose again.</li>
</ul>

<h3>Connected, but no readings appear</h3>
<ol>
<li>Is the <b>Brand</b> in the tab right? Mettler Toledo and Ohaus are asked for each reading;
the other brands must send readings on their own (continuous output).</li>
<li>Is the balance set to {_PORT}? Check the balance's own menu (see its guide).</li>
<li>Is the balance's output mode right? Bonvoisin and Lachoi must be on <b>continuous</b>
output, or they only send when you press their Print key.</li>
<li>Is it the right cable? Most balances need a crossed ("null-modem") cable: balance pin 2 to
computer pin 3, pin 3 to pin 2, ground (pin 5) to pin 5. The Ohaus Adventurer AR has its ground
on pin 7, so use its own Ohaus cable.</li>
</ol>

<h3>Readings are garbled, or only some arrive</h3>
<p>The balance's baud rate, data bits or stop bits don't match {_PORT}. The Ohaus Adventurer AR
leaves the factory at 2400 baud, 7 data bits, 2 stop bits, so it has to be changed.</p>

<h3>Readings jump around</h3>
<ul>
<li>Close the draft shield. Keep the balance away from fans, vents, doors and the pumps.</li>
<li>Check that tubing or the collection vessel doesn't touch the pan, the shield or the case:
any contact pulls on the reading.</li>
<li>Let the balance warm up after switching it on (Lachoi: 2 hours; Ohaus: 20 minutes;
MyWeigh: about 1 hour to reach room temperature).</li>
<li>Level the balance with its feet until the bubble is centred.</li>
</ul>

<h3>The flow rate reads too low at slow flow rates, or the mass stays at 0 then jumps</h3>
<p>The balance's <b>zero tracking</b> (auto-zero) is "correcting" the slow increase in mass back
to zero. Turn it off, or set it as low as it goes. On Bonvoisin balances it is menu
<b>05-ErA</b>; on other balances look for <i>Zero tracking</i>, <i>Auto zero</i> or
<i>AZT</i>. Starting each run with a little liquid already in the vessel (not exactly 0) also
keeps zero tracking out of the way.</p>

<h3>The app's Tare button does nothing</h3>
<p>The app sends the command <code>T</code>, which Mettler Toledo, Ohaus and MyWeigh balances
understand. Balances that only send readings (Bonvoisin, Lachoi) may ignore it: press
<b>TARE</b> on the balance itself.</p>

<h3>Readings stopped in the middle of a run</h3>
<ul>
<li>The cable came loose, or the computer went to sleep. The tab keeps trying to read, so
reconnecting the cable is often enough; otherwise press Connect again.</li>
<li>Readings taken so far are safe in <i>Data Backups</i>: use <b>Recover Session</b> in the
tab if the app was closed.</li>
<li>Details are in the log: Settings &gt; Application Settings &gt; <b>Open Log Folder</b>.
A line "Reading COM12 (...) failed; retrying" means the port stopped answering.</li>
</ul>
"""


BONVOISIN = f"""
<h2>Bonvoisin</h2>
<p>Brand in the tab: <b>Bonvoisin</b>. The app only listens, so the balance must send readings
continuously, at {_PORT}.</p>

<h3>Set up for the app</h3>
<p>Open the balance's setup menu and set:</p>
<ul>
<li><b>08-bud</b> (baud rate): <b>9600</b></li>
<li><b>09-odE</b> (output mode): <b>3</b> (continuous)</li>
<li><b>10-EPE</b> (parity): <b>none</b></li>
<li><b>05-ErA</b> (zero tracking): off, or as low as it goes. This matters for slow flow rates:
see "The flow rate reads too low" in <i>Start here</i>.</li>
<li>Finish with <b>12-off</b> to save and return to weighing.</li>
</ul>

<h3>Menu codes</h3>
{
    _table(
        ["Code", "Name", "What it does"],
        [
            ["01-diu", "Division", "The scale's resolution. Leave at <code>0.01</code>."],
            ["02-PnE", "Point", "Decimal places. <code>2</code> for <code>0.00</code>."],
            ["03-CAP", "Capacity", "Maximum load. <code>5000</code> for the 5 kg balance."],
            ["04-CAL", "Calibration", "External calibration with a reference mass."],
            ["05-ErA", "Error range", "Zero-tracking threshold. Off or lowest for flow measurements."],
            ["06-SLP", "Sleep", "Auto-off timer. Turn it off so the balance can't switch off during a run."],
            ["07-LEd", "Backlight", "Backlight brightness or auto-on."],
            ["08-bud", "Baud rate", "RS-232 speed. <b>9600</b>."],
            [
                "09-odE",
                "Output mode",
                "0 none, 1 manual (Print key), 2 when stable, <b>3 continuous</b> (needed).",
            ],
            ["10-EPE", "Parity", "RS-232 parity. <b>None</b>."],
            ["11-unE", "Unit enable", "Hides units you don't use (like ct or lb)."],
            ["12-off", "Exit", "Saves the changes and returns to weighing."],
        ],
    )
}
<p class="note">Don't change 01-diu, 02-PnE or 03-CAP unless you know the balance needs it: they
change how the balance reads its own sensor, and it then has to be recalibrated.</p>

<h3>Troubleshooting</h3>
<ul>
<li>No readings: check 08-bud = 9600 and 09-odE = 3.</li>
<li>Readings only when the display is steady: 09-odE is on 2 (stable). Set it to 3.</li>
<li>The balance switched itself off during a run: turn off 06-SLP.</li>
<li>Readings are a little off: calibrate with 04-CAL and the reference mass.</li>
</ul>
"""


LACHOI = f"""
<h2>Lachoi (JT-D series, e.g. JT503D)</h2>
<p>Brand in the tab: <b>Lachoi</b>. The app only listens, so the balance must send readings
continuously, at {_PORT}. JT503D: 500 g capacity, 0.001 g readability.
<b>Warm up for 2 hours</b> after switching on.</p>

<h3>Set the baud rate (C3)</h3>
<ol>
<li>Hold <b>Function</b> for more than 3 seconds until <code>C3--03</code> appears.</li>
<li>Press <b>Tare</b> to change it to <code>C3-4</code> (9600 baud).<br>
C3-1 = 1200, C3-2 = 2400, C3-3 = 4800, <b>C3-4 = 9600</b>, C3-5 = 19200, C3-6 = 38400.</li>
</ol>

<h3>Set continuous output (C5)</h3>
<ol>
<li>Hold <b>Function</b> for more than 3 seconds until <code>C3--03</code> appears, then let go.</li>
<li>Press <b>CAL</b> until <code>C5--00</code> appears.</li>
<li>Press <b>Tare</b> to choose <b>C5-0</b> (continuous output).<br>
C5-0 = continuous, C5-1 = sampling (for other software), C5-2 = Print key only,
C5-3 = on command.</li>
</ol>
<p class="note">The manual doesn't say how to leave this menu. After setting it, switch the
balance off and on and check that C3-4 and C5-0 are still set.</p>

<h3>Cable</h3>
<p>Crossed (null-modem) cable: balance pin 2 (RXD) to computer pin 3, balance pin 3 (TXD) to
computer pin 2, ground pin 5 to pin 5.</p>

<h3>Calibrate</h3>
<ol>
<li>Press <b>Tare</b> to zero, with nothing on the pan.</li>
<li>Hold <b>CAL</b> for more than 3 seconds until <code>--CAL-g</code> appears, then let go.</li>
<li>Wait for the mass to show (for example <code>200.000g</code>) and put that reference mass on
the pan.</li>
<li>When the value is displayed, take the mass off. Calibration is done.</li>
</ol>

<h3>Troubleshooting (from the manual)</h3>
{
    _table(
        ["Display", "Cause", "What to do"],
        [
            [
                "<code>______</code> (bottom line)",
                "Zero point is negative",
                "Recalibrate with the reference mass.",
            ],
            ["<code>‾‾‾‾‾‾</code> (top line)", "Overload", "Take the load off and recalibrate."],
            ["Err-1", "Switched on and off repeatedly", "Switch off, wait 3 seconds, switch on."],
            ["Err-2", "Calibration not finished", "Check the surroundings and calibrate again."],
            [
                "Reading unstable",
                "Draughts or vibration, draft shield open, something between pan and draft ring, "
                "unsteady power, or the sample is gaining or losing moisture",
                "Close the shield, clear the pan area, move away from vibration and airflow, "
                "use a steady power supply.",
            ],
            [
                "Reading doesn't match the real mass",
                "Not calibrated, not tared, or not level",
                "Calibrate, press Tare with an empty pan, level it with the feet.",
            ],
        ],
    )
}
"""


OHAUS = f"""
<h2>Ohaus Adventurer</h2>
<p>Brand in the tab: <b>Ohaus Adventurer</b>. The app asks the balance for each reading (the
command <code>IP</code>), so Auto Print stays off. The balance must be set to {_PORT}.
The steps below are for the Adventurer <b>AR</b> series (manual in the archive);
<a href="https://dmx.ohaus.com/WorkArea/showcontent.aspx?id=4294974227">newer Adventurer
manual</a>. <b>Warm up for 20 minutes.</b></p>

<h3>Set up for the app (AR series)</h3>
<p class="note">Out of the box the AR is set to 2400 baud, 7 data bits, 2 stop bits, which the
app can't read. Change all of them:</p>
<ol>
<li>Switch the balance <b>off</b>. Hold <b>&gt;O/T&lt;</b> until <code>MENU</code> appears,
then let go (<code>UNITS</code> shows).</li>
<li>Press <b>Mode Off</b> until <code>PRINT</code> shows, then press <b>&gt;O/T&lt;</b>.</li>
<li><code>bd</code>: press Mode Off until <b>9600</b>, then &gt;O/T&lt;.</li>
<li><code>PAR</code>: <b>no</b>, then &gt;O/T&lt;.</li>
<li><code>DATA</code>: <b>8</b>, then &gt;O/T&lt;.</li>
<li><code>STOP</code>: <b>1</b>, then &gt;O/T&lt;.</li>
<li><code>STBL</code>: <b>OFF</b> (so it answers even while the reading changes), then &gt;O/T&lt;.</li>
<li><code>AUTO</code>: <b>OFF</b>, then &gt;O/T&lt;. <code>END</code> shows: press &gt;O/T&lt; to save.</li>
<li>Press Mode Off until <code>MENU END</code>, then &gt;O/T&lt; to go back to weighing.</li>
</ol>
<p>The menu only saves when you leave it through <code>END</code>.</p>

<h3>Cable</h3>
<p>The AR's 9-pin socket: pin 2 = data out (TXD), pin 3 = data in (RXD), <b>pin 7 = ground</b>
(not pin 5 as on most balances). Use the Ohaus cable for this balance; a cable from another
brand won't work.</p>

<h3>Calibrate (span)</h3>
<ol>
<li>With the balance on, hold <b>&gt;O/T&lt;</b> until <code>CAL</code> appears, then let go.</li>
<li><code>-C-</code> shows, then the mass to use. Don't touch the balance while <code>-C-</code>
shows.</li>
<li>Put that mass on the pan and press &gt;O/T&lt;. When the weight shows, take the mass off.</li>
</ol>
<p>Span masses: 50 g (65 g model), 100 g (110 g), 150 g (150 g), 200 g (210 g), 300 g (310 g),
500 g (510 g), 1500 g (1500 g), 3000 g (3100 g), 4000 g (4100 g). To give up, hold Mode Off:
the old calibration is kept.</p>

<h3>Error codes</h3>
{
    _table(
        ["Code", "Meaning", "What to do"],
        [
            ["Err 2.0", "Not stable", "Move away from vibration and air currents."],
            ["Err 3.0", "Wrong calibration mass", "Calibrate again with the right mass."],
            ["Err 4", "Bad internal data", "Needs servicing."],
            ["Err 6.0", "Parts counting: pieces too light", "(Not used by this app.)"],
            [
                "Err 8.4",
                "Over or under load (also: pan missing)",
                "Check the load and the pan; recalibrate if it happens within capacity.",
            ],
            ["Err 9", "Internal error", "Needs servicing."],
            ["Err 9.8", "Bad calibration or setup data", "Recalibrate; if it stays, needs servicing."],
        ],
    )
}
<p>If an AR balance still sends nothing with these settings, note it in the log or tell
whoever looks after the app: the AR manual lists <code>P</code> as its print command, while the
app sends <code>IP</code> (the newer Adventurer command).</p>
"""


METTLER = f"""
<h2>Mettler Toledo</h2>
<p>Brand in the tab: <b>Mettler Toledo</b>. The app asks for each reading with the MT-SICS
command <code>SI</code> (send the weight now), so no continuous mode is needed.
(<a href="https://www.mt.com/us/en/home/library/operating-instructions/laboratory-weighing/MS-TS_OI.html">Mettler manual</a>)</p>

<h3>Set up for the app</h3>
<p>In the balance's menu, under the RS-232 interface (the menu names vary by model):</p>
<ul>
<li>Mode / device: <b>Host</b> (or <i>MT-SICS</i> / <i>Dialog</i>), not <i>Printer</i>.</li>
<li>{_PORT}.</li>
<li>Auto zero / zero tracking: off for slow flow measurements.</li>
</ul>

<h3>What the balance answers</h3>
{
    _table(
        ["Answer", "Meaning"],
        [
            ["<code>S S   12.345 g</code>", "Stable reading (used)."],
            ["<code>S D   12.345 g</code>", "Reading still changing (also used)."],
            ["<code>S I</code>", "Busy (for example taring or calibrating): no reading this time."],
            [
                "<code>S +</code> / <code>S -</code>",
                "Overload / underload (pan missing): no readings until fixed.",
            ],
            [
                "<code>ES</code>, <code>ET</code>, <code>EL</code>",
                "Command not understood: the interface isn't in Host/MT-SICS mode, or the baud rate is wrong.",
            ],
        ],
    )
}

<h3>Troubleshooting</h3>
<ul>
<li>No readings: the interface is in Printer mode, or not at 9600 baud.</li>
<li>Readings stop while the pan is overloaded or off: the balance answers <code>S +</code> or
<code>S -</code> instead of a weight.</li>
</ul>
"""


OTHER = f"""
<h2>Other balances</h2>
<p>A balance that sends one reading per line, a number and then a unit (for example
<code>+123.456 g</code>), usually works with the <b>Bonvoisin</b> or <b>Lachoi</b> brand
setting, at {_PORT} and in continuous output mode.</p>

<h3>MyWeigh iBalance i211</h3>
<ul>
<li>Brand in the tab: <b>Bonvoisin</b>. It sends at 9600 baud: <code>+(-)XXX.XX UNIT</code>.</li>
<li>Crossed (null-modem) cable: balance pin 2 (RXD) to computer pin 3, pin 3 (TXD) to pin 2,
ground pin 5 to pin 5.</li>
<li>It accepts one-letter commands, so the app's Tare button works: <code>T</code> tare,
<code>U</code> unit, <code>C</code> calibrate, <code>O</code> off.</li>
<li>Calibrate: press <b>CAL</b>, choose <code>SCALE</code> with MODE and press TARE, choose
100 g or 200 g with MODE and press TARE, then put the mass on when the display flashes and
take it off when it stops.</li>
<li><code>Err 1</code>: overload; take the load off. <code>Lo</code>: batteries low; use the
mains adaptor for long runs.</li>
</ul>

<h3>Adam Equipment</h3>
<p>RS-232 menu &gt; PC &gt; Continuous, 9600 baud. Brand in the tab: <b>Bonvoisin</b>.
(<a href="https://www.adamequipment.com/media/docs/Print/EN/Manuals/Nimbus_Manual.pdf">Adam manual</a>)</p>
"""


# Title -> page. The brand titles match the Brand box in a balance tab.
GUIDES = {
    "Start here": COMMON,
    "Bonvoisin": BONVOISIN,
    "Lachoi": LACHOI,
    "Ohaus Adventurer": OHAUS,
    "Mettler Toledo": METTLER,
    "Other balances": OTHER,
}


class BalanceGuidesPage(QWidget):
    """One tab per guide, each a read-only page with clickable links."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.pages = {}
        for title, html in GUIDES.items():
            page = QTextBrowser()
            page.setOpenExternalLinks(True)
            page.document().setDefaultStyleSheet(_STYLE)
            page.setHtml(html)
            self.tabs.addTab(page, title)
            self.pages[title] = page

    def show_guide(self, title):
        """Bring up the guide with this title (a brand name); "Start here" if there is none."""
        page = self.pages.get(title, self.pages["Start here"])
        self.tabs.setCurrentWidget(page)
        return page
