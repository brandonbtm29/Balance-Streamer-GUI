# Balance Streamer Application

A Python-based standalone GUI application designed to connect to multiple laboratory analytical balances simultaneously via serial communication (RS-232 / USB). It logs the data, processes live flow rates using advanced customizable derivative engines (Savitzky-Golay, Butterworth, EMA), and features Excel exporting and session recovery.

## Technology Stack
- **Framework**: `PyQt6` (with `pyqtdarktheme` for dark mode)
- **Serial Comms**: `pyserial`
- **Data Plotting**: `matplotlib` (QtAgg Backend)
- **Data Analytics**: `scipy` (Savitzky-Golay, Linear Regression, Butterworth Filtering)
- **Exporting**: `openpyxl` (Generates native `.xlsx` files with embedded ScatterCharts)

## Supported Balances
The built-in parser engine natively understands data formats from:
- Bonvoisin
- Mettler Toledo (MT-SICS protocol)
- Ohaus Adventurer
- Lachoi

## Running the Application
### From Source
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python multi_balance_stream.py
   ```

### Building an Executable
To create a standalone executable for macOS (`.app`) or Windows (`.exe`):
1. Install dependencies.
2. Run the build script:
   ```bash
   python build_app.py
   ```
3. The executable will be generated inside the `dist/Balance_Streamer/` directory.

## Data Backups
All emergency session backups (to protect against power loss or crashes) are automatically saved as `.csv` files inside the `Data Backups/` folder. They are pruned automatically on a rolling 30-day basis.
