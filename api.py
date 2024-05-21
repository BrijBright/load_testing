from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):
    
    @task(1)
    def get_posts(self):
        self.client.get("/posts")

    @task(2)
    def get_post(self):
        post_id = 1
        self.client.get(f"/posts/{post_id}")

    @task(3)
    def create_post(self):
        self.client.post("/posts", json={
            "title": "foo",
            "body": "bar",
            "userId": 1
        })

    @task(4)
    def update_post(self):
        post_id = 1
        self.client.put(f"/posts/{post_id}", json={
            "id": 1,
            "title": "foo",
            "body": "bar",
            "userId": 1
        })

    @task(5)
    def delete_post(self):
        post_id = 1
        self.client.delete(f"/posts/{post_id}")

class WebsiteUser(HttpUser):
    host="https://jsonplaceholder.typicode.com"
    tasks = [UserBehavior]
    wait_time = between(1, 5)
