# Fusion 360 project setup

`Symm60HECaseSetup/` is a Fusion 360 script that builds the case-design
project from the generated reference bodies in this directory, so the case
work starts from a consistent, named component tree instead of a manual
STEP import.

Install once by copying the `Symm60HECaseSetup` folder to
`%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\`, then in Fusion press
**Shift+S** (UTILITIES > ADD-INS > Scripts and Add-Ins), select
`Symm60HECaseSetup` and click **Run**. The script:

1. creates a new millimetre design named `Symm60HE Case`;
2. imports the nine placed `Symm60HE-*.step` bodies into
   `Reference (do not edit)`, grouped as PCBs, Plates, Switches and Keycaps
   (switch and keycap banks are semi-transparent and every reference is
   grounded);
3. imports the Neo pogo and mounting references into a hidden
   `Pogo references (optional)` component, controlled by the flags at the top
   of the script;
4. creates empty `Case` components (`Left top`, `Left bottom`, `Right top`,
   `Right bottom`, `Controller housing`) and activates `Case`;
5. saves the design into a `Symm60HE Case` folder of the active Fusion
   project when Fusion is signed in.

`REFERENCE_DIR` at the top of the script points at this directory; change it if
the repository is moved. The script only reads the STEP files.
