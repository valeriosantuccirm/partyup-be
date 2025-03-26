# ADJUST WHEN READY TO RELEASE!

# PartyUp

PartyUp is a social media app designed to help users discover, create, and join events. It focuses on bringing people together for various activities and allows users to interact in real-time, similar to platforms like Meetup, but with a more dynamic and engaging experience.

## Features

- **User Authentication**: Users can sign up and log in using their Google or Apple accounts via Firebase Authentication.
- **Event Creation & Management**: Users can create events with various options, including:
  - Set maximum attendees
  - Request donations (with fees for the app)
  - Set event cover images
  - Schedule events (up to one month in advance for regular users, beyond that for premium users)
- **Event Types**: Events can have multiple statuses: **UPCOMING**, **ONGOING**, **OUTDATED**, **CANCELLED**, and **POSTPONED**.
- **Premium Features**: Premium users can create events scheduled beyond one month and access certain features like skipping the join queue.
- **Real-Time Interaction**: Users can interact with ongoing events, including uploading media and participating in live discussions.
- **Friend Requests**: Users can send, accept, or decline friend requests, with notifications being sent to both parties.
- **Event Leaderboards**: A leaderboard displaying user-generated content related to joined events, encouraging engagement.
- **Push Notifications**: Users receive in-app or push notifications for various activities, including friend requests and event updates.

## Tech Stack

- **Frontend**: (This section can include your frontend framework or mention if you're building it yourself)
- **Backend**: FastAPI
- **Database**: PostgreSQL (using SQLAlchemy and SQLModel for ORM)
- **Authentication**: Firebase Authentication (Google and Apple login)
- **Real-Time Notifications**: Firebase Cloud Messaging (FCM)
- **Search**: Elasticsearch (for efficient event retrieval)
- **Caching**: Redis (for fast access to recent events)
- **Media Storage**: AWS (for storing event media such as images and videos)
- **Deployment**: Docker (for containerized deployments)

## 🚀 LocalStack S3 Setup for PartyUp

This guide helps you **set up LocalStack** using Docker to **emulate AWS S3 locally** for development. This allows you to test file uploads (e.g., event cover images) without using a real AWS account.

### 📌 Prerequisites
- **Docker** installed → [Download Here](https://www.docker.com/get-started/)
- **AWS CLI** installed → [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- **Python & boto3** installed

To check if Docker is installed, run:
```bash
$ docker --version
```

### 1️⃣ Run LocalStack in Docker
Start LocalStack with S3 support:
```bash
docker run -d --name localstack -p 4566:4566 -p 4510:4510 -e LOCALSTACK_UI=true -e SERVICES=s3 -e S3_BUCKET_NAME=partyup-events -e S3_ENDPOINT_URL=http://localstack:4566 -e DEFAULT_REGION=us-east-1 -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test localstack/localstack
```

#### 🔹 Explanation
✅ `-d` → Runs in the background  
✅ `-p 4566:4566` → Exposes LocalStack services (S3 runs on `4566`)  
✅ `-e SERVICES=s3` → Starts only **S3** (you can add more services)  
✅ `-e AWS_ACCESS_KEY_ID=test` & `AWS_SECRET_ACCESS_KEY=test` → Fake AWS credentials for local testing  

### 2️⃣ Configure AWS CLI for LocalStack
Run the following commands to set up AWS CLI:
```bash
awslocal s3api create-bucket --bucket partyup-events
```

### Create an S3 Bucket in LocalStack
```bash
awslocal --endpoint-url=http://localhost:4566 s3 mb s3://partyup-events
```
✔️ You now have an **S3-compatible bucket** called `partyup-events` running locally!

### 4️⃣ Testing Your Setup
#### ✅ List Buckets
```bash
awslocal --endpoint-url=http://localhost:4566 s3 ls
```

#### ✅ List Files in Bucket
```bash
awslocal --endpoint-url=http://localhost:4566 s3 ls s3://partyup-events/
```

### 🔥 Done! You now have a local S3 setup for free! 🎉
This setup **mimics AWS S3** but runs on your **own machine**, so there are **zero costs** while developing. Later, you can **swap `endpoint_url` to AWS S3** for production.

---

## Encryption for Sensitive Files (e.g., `.env`)

To securely manage sensitive files such as the `.env` that contains environment variables, you can encrypt the file before versioning it in your repository.

### Steps for Encrypting `.env`:

1. **Encrypting the File**
   Use **GPG** (GNU Privacy Guard) to encrypt the `.env` file:

   ```bash
   gpg -c --cipher-algo AES256 .env
   ```

   This will create an encrypted file called `.env.gpg`.

2. **Decryption for Use**
   When needed, decrypt the file for use with the following command:

   ```bash
   gpg -d .env.gpg > .env
   ```

3. **Adding to `.gitignore`**
   Make sure to add `.env` and other sensitive files to your `.gitignore` so they are not accidentally versioned:

   ```bash
   .env
   ```

4. **Securely Versioning Encrypted Files**
   You can now safely version `.env.gpg` in your repository, ensuring that sensitive information is kept private.

---

## Installation

### Prerequisites

- Python 3.8+ (with virtualenv recommended)
- PostgreSQL (for local development)
- Docker (for containerized environments)
- Firebase project (for authentication and cloud messaging)

### Steps to Run Locally

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/partyup.git
   cd partyup
   ```

2. **Create, Activate a Virtual Environment and Install Dependencies**

   ```bash
   pipenv install --python 3.13.2 # Python version requird
   pipenv shell
   ```

3. **Setup Firebase**

   - Set up Firebase Authentication and Firebase Cloud Messaging in your Firebase Console.
   - Download your Firebase service account JSON file and place it in your project folder. Make sure to **never** commit this file to your version control system. You can use `.gitignore` to exclude it.

4. **Configure the `.env` File**

   Create a `.env` file in the root of the project and add the following variables:

   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/partyup_db
   FIREBASE_CONFIG_PATH=path_to_your_firebase_config.json
   REDIS_URL=redis://localhost:6379
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   ```

5. **Create the Database Schema**

   Run the database migrations (you can use Alembic for this, or use SQLModel to create the database schema):

   ```bash
   alembic upgrade head
   ```

6. **Run the Application**

   Start the FastAPI app:

   ```bash
   uvicorn app.main:app --reload
   ```

   The app will be available at `http://localhost:8000`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
