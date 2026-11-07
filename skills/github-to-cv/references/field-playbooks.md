# Field playbooks

For each field: what recruiters scan for, which GitHub signals matter, keyword clusters to check
against the JD, the section order and template to use, and common mistakes. Keyword lists are
starting points. The JD always wins, and only true skills go in.

---

## Backend engineering
- **Scan for:** scale (req/s, data volume), reliability (SLOs, incidents), API design, data stores, distributed systems, cloud.
- **GitHub signals:** services/libraries with tests and CI, benchmarks in READMEs, published packages, Docker/Helm/Terraform files, merged PRs to infrastructure libraries.
- **Keywords:** Go, Java, Python, Node.js, Kotlin, REST APIs, gRPC, GraphQL, microservices, PostgreSQL, MySQL, Redis, Kafka, RabbitMQ, message queues, event-driven architecture, AWS/GCP/Azure, Docker, Kubernetes, CI/CD, observability, distributed systems, system design, caching, concurrency.
- **Order:** summary → skills → experience → projects → open source → education. Template: `modern`, or `minimal` for big tech.
- **Mistakes:** listing endpoints instead of outcomes; no numbers for latency, throughput or availability.

## Frontend engineering
- **Scan for:** shipped UI at scale, performance (Core Web Vitals, bundle size), accessibility, design systems, testing.
- **GitHub signals:** live demos (homepage URL), component libraries, Storybook, Lighthouse scores, npm packages.
- **Keywords:** TypeScript, JavaScript, React, Next.js, Vue.js, Angular, Svelte, Redux, Tailwind CSS, HTML, CSS, accessibility (WCAG), responsive design, web performance, SSR, testing (Jest, Testing Library, Playwright, Cypress), design systems, Storybook, Webpack/Vite.
- **Order:** summary → skills → experience → projects (with live links) → education. Template: `modern`.
- **Mistakes:** no live links; "made a website" with no users or performance numbers; skill lists heavy on CSS frameworks.

## Full-stack
- Combine backend and frontend: lead with end-to-end products you shipped (users, revenue, adoption).
- **Keywords:** TypeScript, React/Next.js, Node.js/Express/NestJS or Python/Django/FastAPI, PostgreSQL/MongoDB, REST/GraphQL, auth (OAuth 2.0, JWT), Docker, CI/CD, AWS/Vercel.
- Template: `modern` (experienced) or `compact` (students).

## Mobile
- **Scan for:** apps in stores (downloads, ratings), crash-free rate, performance, offline/sync, release cadence.
- **GitHub signals:** Swift/Kotlin/Dart repos, app store links in READMEs, Compose/SwiftUI usage.
- **Keywords:** iOS, Swift, SwiftUI, UIKit, Android, Kotlin, Jetpack Compose, React Native, Flutter, Dart, REST APIs, Firebase, CI/CD (Fastlane), app performance, accessibility.
- Put **store links and downloads** in project bullets. Template: `modern`.

## Data science / ML / AI
- **Scan for:** models in production, measurable business or metric impact, experimentation rigour, data scale; for GenAI: LLM apps, evaluation, RAG, fine-tuning.
- **GitHub signals:** notebooks *with clear results*, packaged libraries, model cards, Hugging Face links, Kaggle medals, papers.
- **Keywords:** Python, SQL, PyTorch, TensorFlow, scikit-learn, pandas, NumPy, statistics, A/B testing, experimentation, feature engineering, NLP, computer vision, LLMs, RAG, fine-tuning (LoRA), evaluation, Hugging Face, MLOps, MLflow, Spark, Airflow, AWS SageMaker/GCP Vertex AI, model deployment.
- **Bullets:** metric → baseline → result ("F1 0.71 → 0.84"), plus business impact ("cut manual review by 35%").
- **Order:** summary → skills → experience → projects → publications → education. Template: `modern` (`academic` for research roles).
- **Mistakes:** featuring course notebooks (Titanic, MNIST, MOOC exercises); accuracy without a baseline; tools without outcomes.

## Data engineering
- **Scan for:** pipelines at scale (rows/day, TB), reliability (SLAs, data quality), cost, modelling, streaming.
- **Keywords:** SQL, Python, Scala, Spark/PySpark, Airflow, dbt, Kafka, Flink, Snowflake, BigQuery, Redshift, Databricks, data warehousing/lakehouse, ETL/ELT, data modelling, data quality (Great Expectations), AWS/GCP, Terraform.
- Template: `modern`.

## DevOps / SRE / Cloud / Platform
- **Scan for:** availability (SLOs, MTTR), deployment frequency, cost savings, migrations, IaC coverage, incident leadership, security posture.
- **GitHub signals:** Terraform modules, Helm charts, operators/controllers, GitHub Actions, Ansible roles, CLI tools.
- **Keywords:** AWS/GCP/Azure, Kubernetes, Docker, Terraform, Helm, Ansible, CI/CD, GitHub Actions/GitLab CI/Jenkins, Argo CD/GitOps, Prometheus, Grafana, OpenTelemetry, observability, SRE, incident response, Linux, networking, Bash, Python/Go, cost optimisation, security/IAM.
- **Bullets:** "Cut deploy time from 45 to 8 min", "Raised availability to 99.95%", "Saved $180k/yr".
- Template: `modern` or `executive` (senior/staff).

## Security
- **Scan for:** findings and their impact, tooling built, compliance delivered, incidents handled, certifications (OSCP, CISSP, CEH), CVEs and bug bounties.
- **GitHub signals:** security tools, CTF write-ups, detection rules, CVE PoCs. Check ethics and permissions before featuring exploits.
- **Keywords:** application security, OWASP, threat modelling, penetration testing, vulnerability management, SAST/DAST, SIEM (Splunk), incident response, cloud security, IAM, zero trust, cryptography, compliance (SOC 2, ISO 27001, PCI DSS), Python, Burp Suite.
- Certifications section is important. Template: `modern` or `classic`.

## Embedded / IoT / Robotics
- **Scan for:** hardware brought up, constraints met (memory, power, real-time), protocols, products shipped, safety standards.
- **Keywords:** C, C++, Embedded C, RTOS (FreeRTOS, Zephyr), ARM Cortex-M, STM32, ESP32, Embedded Linux, Yocto, device drivers, UART/SPI/I2C/CAN, MQTT, IoT, ROS/ROS 2, control systems, FPGA, Verilog/VHDL, Python for test automation.
- Link photos or videos of hardware via the project URL, not embedded images. Template: `modern` or `classic`.

## Game development
- **Keywords:** Unity, C#, Unreal Engine, C++, Godot, gameplay programming, rendering, shaders (HLSL/GLSL), physics, multiplayer/networking, optimisation, profiling, tools, console/mobile platforms.
- Shipped titles (platform, downloads/ratings) and game jams are key evidence. Use project URLs for playable builds.

## Research / academia
- **Order:** research interests → education → publications → research experience → research software → awards → teaching → talks → service → skills. Template: `academic`.
- Publications: authors in order with the candidate's name **bold** (automatic), venue, year, link. Mark "Oral", "Spotlight" or "Best Paper" in `note`.
- Research code: stars, citations, downstream users. Add "Teaching", "Talks" and "Service" with `customSections`.

## Web3 / blockchain
- **Keywords:** Solidity, Ethereum, smart contracts, Hardhat/Foundry, EVM, DeFi, security audits, gas optimisation, ethers.js/viem, Rust/Solana, TypeScript.
- Evidence: audited contracts, TVL/volume (if real and verifiable), audit findings, bug bounties.

## Career switchers (any target)
- Lead with a bridging summary. Make the transferable domain an asset ("Former nurse building healthcare data tools").
- Feature projects that match the target role; keep previous roles with 1–2 transferable, quantified bullets.
- Template: `modern` or `classic`.
