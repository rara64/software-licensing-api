# Software Licensing API

This is a university project developed with **Python (Flask)** and **MongoDB**, as a part of the Non-Relational Database Solutions course. 

## Getting Started

1. **Run the Setup Wizard:**
    ```bash
    python setup_wizard.py
    ```
    This will guide you through configuring the `.env` file for the API.
2. **Run the API:**
   ```bash
   python app.py
   ```
   API will be available at port `5000`.
3. **Checkout the project's wiki:**
   - [Project's wiki](https://github.com/rara64/software-licensing-api/wiki)

## API Endpoints

List of all available endpoints is in the project's wiki:

-   [**List of Endpoints**](https://github.com/rara64/software-licensing-api/wiki/List-of-endpoints)

**Basic Endpoints:**

| Endpoint      | Description                                    |
| ------------- | ---------------------------------------------- |
| `/`           | A way to check if the API works   |
| `/users`      | CRUD operations for users                      |
| `/licenses`   | CRUD operations for licenses                   |
| `/checksums`  | CRUD operations for checksums                 |
| `/auth`       | Authentication endpoint                        |
| `/activate`   | Endpoint to activate a software license       |

## API Security Overview

- Most endpoints are available only to authenticated users.
- Secrets are stored in a `.env` file.
- Each user authenticates using a JWT token which holds the user ID and an expiry date.
- Users acquire JWT tokens using the `/auth` endpoint by providing a valid username and password.
  - On top of that, admin user has to provide a one-time password when 2FA is enabled.
- Most CRUD operations are not available to normal users.
- Only the admin user created using the setup wizard can perform full CRUD operations.

## Licensing System Overview

Project uses **RSA 2048-bit** cryptography keys for generating and veryfing signatures which are treated as license files.
-   Each license key is tied to a unique hardware ID, preventing use on other machines.
-   API uses a private key to sign licenses, and a matching public key is used to verify them.

| **API**     | **Application**  |
| ------------- | ------------------------------------------ |
| Holds the **PRIVATE KEY** 🔑 | Holds the **PUBLIC KEY** 🔑 |

### Activation Process

1. Application sends a request to the `/activate` endpoint. This request includes:
    -   License key
    -   Hardware information identifying the machine
2. API verifies the provided information and uses its **PRIVATE KEY** 🔑 to generate a signature for the hardware data.
3. Application receives the signature and saves it in a license file.

### Verification Process

1. Application grabs the following:
    -   Signature from the license file
    -   License key
    -   Current hardware ID of the machine
2. Application uses its **PUBLIC KEY** 🔑 to verify the signature against the current hardware ID. If the verification is successful, the software is considered licensed.

## Demo Application

You can find a demo application written in C# to test the licensing system here: [Demo .NET 8 C# Application](https://github.com/rara64/software-licensing-api/blob/main/demo_app/Program.cs)
