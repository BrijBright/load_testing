from locust import HttpUser,constant,between,task,SequentialTaskSet,TaskSet
from faker import Faker
import logging
import random
import re

class UserBehavior(SequentialTaskSet):
    wait_time=between(1,5)
    def __init__(self,parent):
        super().__init__(parent)
        self.fake = Faker('en_US') #generate fake data for testing
        self.csrf=''
        self.first_name=''
        self.last_name=''
        self.email=''
        self.phone_number=0
        self.password=''
        self.confirm_password=''
        

    def on_start(self):
        #getting registration page
        with self.client.get('/accounts/register/',catch_response=True,name='1. getting registration page') as response1:
            if response1.status_code==200 and "Sign up" in response1.text:
                self.csrf=response1.cookies.get('csrftoken') #getting csrf token 
                response1.success()
            else:
                response1.failure(f'not able to get registration page --{response1.status_code} error')
        
        #preparing data for registration
        try:
            
            self.first_name=self.fake.first_name()
            self.last_name=self.fake.last_name()
            self.email=self.fake.email()
            self.phone_number=self.fake.phone_number()
            self.password=self.fake.password()
            self.confirm_password=self.password
        except Exception as ex :
            logging.critical(f"An error occurred while generating fake data: {ex}") 
            # raise SystemExit("An error occurred while generating fake data. Exiting...") # raise exception and stop program


        #register the user
        register_data={
            "csrfmiddlewaretoken":self.csrf,
            "first_name":self.first_name, 
            "last_name":self.last_name, 
            "email":self.email, 
            "phone_number": self.phone_number,
            "password": self.password,
            "confirm_password":self.confirm_password,
        }

        with self.client.post('/accounts/register/',data=register_data,catch_response=True,name='2. register ther user') as response2:
            if response2.status_code==200 and self.email in response2.text:
                response2.success()
            else:
                response2.failure(f'not able to register --{response2.status_code}-error')
        

        # login the user
        login_data={

            "csrfmiddlewaretoken":self.csrf,
            "email":self.email,
            "password": self.password,
        }
        with self.client.post('/accounts/login/',data=login_data,catch_response=True,name='3. login ther user') as response3:
            if response3.status_code==200 and 'Total Orders' in response3.text:
                response3.success()
            else:
                response3.failure(f'not able to login --{response3.status_code}-error')

    @task
    class DashboardTask(SequentialTaskSet):
        wait_time=between(1,5)
        @task 
        def varify_orders(self):
            with self.client.get('/accounts/my_orders/',catch_response=True,name='4. varify orders') as v_response:
                if 'Your order history' in v_response.text:
                    v_response.success()
                else:
                    v_response.failure(f'not able to get orders--{v_response.status_code}--failure')

        @task
        def varify_change_password(self):
            #get pass change page
            with self.client.get('/accounts/change_password/',catch_response=True,name='5. getting pass change page') as cp_response:
                if 'Change Your Password' in  cp_response.text:
                    cp_response.success()
                    self.parent.csrf=cp_response.cookies.get('csrftoken')
                else:
                    cp_response.failure(f'not able to get change password page --{cp_response.status_code}--error')

            #changing password
            #praparing new password data
            new_pass=self.parent.fake.password()
            new_pass_data={
                'csrfmiddlewaretoken':self.parent.csrf,
                'current_password': self.parent.password,
                'new_password':new_pass,
                'confirm_password':new_pass,
            }
            self.parent.password=new_pass
           

            # changing password 
            with self.client.post('/accounts/change_password/',catch_response=True,name='6. changing the password',data=new_pass_data) as np_response:
                if 'Login' in np_response.text:
                    np_response.success()
                else:
                    np_response.failure(f'not able to change password--{np_response.status_code}')

            #login after password change
            login_data={

            "csrfmiddlewaretoken":self.parent.csrf,
            "email":self.parent.email,
            "password": self.parent.password,
        }
            with self.client.post('/accounts/login/',data=login_data,catch_response=True,name='7. login after pass change') as response:
                if response.status_code==200 and 'Total Orders' in response.text:
                    response.success()
                else:
                    response.failure(f'not able to login --{response.status_code}-error')

        @task
        def stop(self):
            if random.randint(1, 4)==3:
                self.interrupt()

    #  product selecting and buying
    @task 
    class select_product(SequentialTaskSet):
        wait_time=between(1,5)
        def __init__(self,parent):
            super().__init__(parent)
            self.categories=['/store/category/shirts/','/store/category/jacket/',
            '/store/category/jeans/','/store/category/shoes/','/store/category/t-shirt/']

            self.selected_product=''

        def extract_action_color_size(self,text):
                action_pattern = re.compile(r'<form\s+action=(?:"|\')(.*?)(?:"|\')')
                color_pattern = re.compile(r'<option value="(\w+)">')
                size_pattern = re.compile(r'<option value="(\d+)">')
                action_matches = action_pattern.finditer(text)
                action_urls = [match.group(1) for match in action_matches]
                action_url = action_urls[1] if len(action_urls) > 1 else None
                color_options = color_pattern.findall(text)
                size_options = size_pattern.findall(text)
                random_color = random.choice(color_options) if color_options else None
                random_size = random.choice(size_options) if size_options else None
                return action_url, random_color, random_size

        def find_urls_followed_by_string(self,pattern, text):
                def escape_special_chars(string):
                    return re.escape(string)

                pattern = '|'.join(map(escape_special_chars, pattern))

                # Adjusted regex pattern to extract href attribute values of <a> tags
                regex_pattern = re.compile(rf'<a\s+href=(?:"|\')((?:{pattern})\S+)(?:"|\')')

                # Finding matches in the text
                matches = regex_pattern.findall(text)
                
                return matches

        @task
        def select_catagories(self):
            random_category_url = random.choice(self.categories)
            self.selected_catagories=random_category_url

            with self.client.get(random_category_url,catch_response=True,name='8. select product catagories') as response:
                if 'items found' in response.text:
                    self.selected_product=random.choice(self.find_urls_followed_by_string(self.categories,response.text))
                    
                    response.success()

                else:
                    response.failure(f'not able to find product catagories --{response.status_code}-error')

        @task
        def select_product(self):
            with self.client.get(self.selected_product,catch_response=True,name='9. selecting product') as response:
                if 'Choose Color' in response.text:
                    self.action_url, self.random_color, self.random_size=self.extract_action_color_size(response.text)  # getting url color size of selected product
                    self.parent.csrf=response.cookies.get('csrftoken')
                    response.success()
                else:
                    response.failure(f'not able to select product--{response.status_code}--error')
            

            product_data={
                'color':self.random_color,
                'size':self.random_size,
                'csrfmiddlewaretoken':self.parent.csrf
            }
            with self.client.post(self.action_url,data=product_data,catch_response=True,name='_10. adding product to cart') as response:
                if 'Product' and 'Quantity' and 'Price' in response.text:
                    response.success()
                else:
                    response.failure(f'not able to add to cat---{response.status_code}--error')
        @task            
        def stop(self):
            if random.randint(1, 4)==3:
                self.interrupt()

    @task
    class checkout_payment(SequentialTaskSet):
        wait_time=between(1,5)
        # getting checkout page
        @task
        def getting_checkout_page(self):
            with self.client.get('/cart/checkout/',catch_response=True,name='_11. getting checkout page') as response:
                if 'Billing Address' in response.text:
                    self.parent.csrf=response.cookies.get('csrftoken')
                    response.success()
                else:
                    response.failure(f'not able to get checkout page --{response.status_code}--error')

        @task
        def checkout(self):
            checkout_data={
                    "csrfmiddlewaretoken":self.parent.csrf,
                    "first_name": self.parent.fake.first_name(),
                    "last_name": self.parent.fake.last_name(),
                    "email": self.parent.fake.email(),
                    "phone": self.parent.fake.phone_number(),
                    "address_line_1": self.parent.fake.street_address(),
                    "address_line_2": self.parent.fake.secondary_address(),
                    "city": self.parent.fake.city(),
                    "state": self.parent.fake.state(),
                    "country": self.parent.fake.country(),
                    "order_note": self.parent.fake.sentence(),
    
                    }
            
            with self.client.post('/orders/place_order/',data=checkout_data,catch_response=True,name='_12. checkout') as response:
                if 'Review Your Order and Make Payment' in response.text:
                    response.success()
                else:
                    response.failure(f'not able to checkout{response.status_code}--error')



        @task
        def stop(self):
            if random.randint(1, 5)==3:
                self.interrupt()






            

class WebsiteUser(HttpUser):
    host="http://brijkishor.pythonanywhere.com/"
    tasks=[UserBehavior]