# 🔒 Software Licensing API

This is a university project developed with **Python (Flask)** and **MongoDB**, as a part of the Non-Relational Database Solutions course. 

## **Getting Started**
1. **Create a virtual python environment**
2. **Install required packages**
   <br>Run the command listed below to install all of the required packages.
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Setup Wizard**  
   The setup wizard will guide you through configuring the `.env` file for the API.
   ```bash
   py setup_wizard.py
   ```

4. **Run the API**  
   API will be available at `https://localhost:5000`.
   ```bash
   py app.py
   ```

5. **Check out the Project's Wiki**  
   For detailed documentation, [visit the wiki](https://github.com/rara64/software-licensing-api/wiki).

## API Endpoints

**List of basic endpoints:**

| Endpoint                | Description                                                                                                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------------- |
| `GET /`                | A way to check if the API works                                                                             |
| `GET /users`<br>`POST /users` | CRUD operations for users <br> `GET`: List users <br> `POST`: Create a user <br> (Other methods: `PUT`, `DELETE`) |
| `GET /licenses`<br>`POST /licenses` | CRUD operations for licenses <br> `GET`: List licenses <br> `POST`: Create a license <br> (Other methods: `PUT`, `DELETE`) |
| `GET /checksums`<br>`POST /checksums` | CRUD operations for checksums <br> `GET`: List checksums <br> `POST`: Create a checksum <br> (Other methods: `PUT`, `DELETE`) |
| `POST /auth`            | Authentication endpoint                                                                                     |
| `POST /activate`        | Endpoint to activate a software license                                                                    |

All endpoints are documented in the wiki:
-   [**Endpoints**](https://github.com/rara64/software-licensing-api/wiki/endpoints)
    -  [API Check](https://github.com/rara64/software-licensing-api/wiki/endpoints#api-check)
    -  [Authenticate](https://github.com/rara64/software-licensing-api/wiki/endpoints#authenticate)
    -  [Activate a software license](https://github.com/rara64/software-licensing-api/wiki/endpoints#activate-a-software-license)
    -  [Users Collection](https://github.com/rara64/software-licensing-api/wiki/endpoints#users-collection)
    -  [Licenses Collection](https://github.com/rara64/software-licensing-api/wiki/endpoints#licenses-collection)
    -  [Checksums Collection](https://github.com/rara64/software-licensing-api/wiki/endpoints#checksums-collection)

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
