# Open the NanoSelect webpage

1. Open C:\Users\Rohan\Desktop\IDP 2026.
2. Double-click run.bat.
3. Your browser opens the local NanoSelect webpage. Keep its terminal window open while using it.

The normal address is http://127.0.0.1:8765/. If that port belongs to another program, the launcher prints an alternate address. The page uses the saved model and evidence on this PC. No Jupyter notebook, internet connection or retraining is required.

## Use the interface

- Choose a pollutant and enter concentration, pH, dose, temperature, contact time and available light.
- Open Treatment setup and assumptions to change equipment, water source, TiO2 formulation, ML inclusion or a removal target.
- Click Rank materials to recompute results.
- The buttons across the top load working examples: SMX under UV, SMX without light, source matched lead conditions and an unsupported pollutant.
- Results show the shortlist, any eligible ML estimate and all 15 materials. Click View beside a material for reasons and research sources.
- Use Export CSV to save the current analysis.

Unknown inputs remain unknown. A decision score is not removal percentage. The ML output is the reported mlogk target, and only supported TiO2 conditions receive a numerical estimate.

## Stop or reopen

To stop the local server, focus its terminal and press Ctrl+C. Double-click run.bat again to reopen it. If the same webpage server is already running, the launcher reuses it.

If the browser does not open automatically, paste the HTTP address printed in the terminal into Chrome or Edge.

## Optional terminal mode

From the IDP 2026 folder, run run.bat --check to check readiness or run.bat --text for the terminal example. The earlier notebooks remain supporting development artifacts; the webpage is the main interface.
