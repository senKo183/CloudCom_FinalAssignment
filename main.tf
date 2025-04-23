resource "google_cloud_run_service" "quiz-app" {
  name     = "quiz-app"
  location = var.region
  project  = "quiz-app-457308"

  template {
    spec {
      containers {
        image = "docker.io/yuj1n/quizapp:v2"
        
        env {
          name  = "MONGODB_USERNAME"
          value = "root"
        }
        
        env {
          name  = "MONGODB_PASSWORD"
          value = "12345"
        }
        
        env {
          name  = "MONGODB_CLUSTER"
          value = "cluster0.boqzife.mongodb.net"
        }
        
        env {
          name  = "MONGODB_DATABASE"
          value = "quizapp"
        }

        env {
          name  = "SECRET_KEY"
          value = "quizapp123"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
} 