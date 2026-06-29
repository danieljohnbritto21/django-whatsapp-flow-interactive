import requests
import json
import logging
import uuid
import os
from django.conf import settings

# Configure logger
logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service to interact with WhatsApp Cloud API"""

    # WhatsApp Cloud API interactive-list constraints (safe defaults)
    _LIST_MAX_SECTIONS = 1
    _LIST_MAX_ROWS_PER_SECTION = 10
    _ROW_TITLE_MAX_LEN = 24
    _ROW_DESC_MAX_LEN = 72
    _SECTION_TITLE_MAX_LEN = 24
    _BODY_MAX_LEN = 1024

    def __init__(self):
        logger.info("=" * 60)
        logger.info("INITIALIZING WhatsAppService")
        self.api_url = "https://graph.facebook.com/v23.0"
        self.phone_number_id = settings.PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_TOKEN
        self.verify_token = settings.VERIFY_TOKEN
        self.flow_id = getattr(settings, 'FLOW_ID', '1458360002725146')
        self.header_image_id = getattr(settings, 'HEADER_IMAGE_ID', None)
        self.header_image_url = getattr(settings, 'WHATSAPP_HEADER_IMAGE_URL', None)
        self._cached_header_media_id = None
        logger.info(f"Phone Number ID: {self.phone_number_id}")
        logger.info(f"Flow ID: {self.flow_id}")
        logger.info(f"Header Image ID: {self.header_image_id}")
        logger.info(f"Header Image URL: {self.header_image_url}")
        logger.info("WhatsAppService initialized successfully")
        logger.info("=" * 60)

    def _get_header_media_id(self):
        """Get or upload the header image media ID. Returns None if fails."""
        logger.debug("_get_header_media_id() called")
        
        # Return cached media ID if available
        if self._cached_header_media_id:
            logger.info(f"Using cached header media ID: {self._cached_header_media_id}")
            return self._cached_header_media_id

        # Use pre-configured media ID if available
        if self.header_image_id:
            logger.info(f"Using pre-configured header media ID: {self.header_image_id}")
            self._cached_header_media_id = self.header_image_id
            return self._cached_header_media_id

        # Try to upload the local image
        try:
            logger.info("Attempting to upload header image to WhatsApp...")
            
            # Prefer an explicit path from settings
            from django.conf import settings as django_settings

            image_path = getattr(django_settings, 'WHATSAPP_HEADER_IMAGE_PATH', None)
            if not image_path:
                # Fallback to default media location
                image_path = os.path.join(settings.MEDIA_ROOT, 'whatsapp_images', 'thaagam_logo.png')
                logger.info(f"Using default image path: {image_path}")

            if not os.path.exists(str(image_path)):
                logger.warning(f"Header image not found at {image_path}")
                return None

            logger.info(f"Image found at: {image_path}")

            url = f"{self.api_url}/{self.phone_number_id}/media"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
            }

            logger.info(f"Uploading to URL: {url}")
            
            with open(image_path, 'rb') as f:
                files = {'file': ('thaagam_logo.png', f, 'image/png')}
                data = {'messaging_product': 'whatsapp', 'type': 'image/png'}
                response = requests.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()
                result = response.json()
                
            media_id = result.get('id')
            if media_id:
                self._cached_header_media_id = media_id
                logger.info(f"Header image uploaded successfully! Media ID: {media_id}")
                return media_id
            else:
                logger.warning("No media ID returned from upload response")

        except Exception as e:
            logger.error(f"Error uploading header image: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

        logger.warning("Returning None - no header media ID available")
        return None

    def _get_interactive_header(self, header_text=None, use_link=False):
        """
        Reusable helper to build a valid header for interactive messages.

        Args:
            header_text: Optional text for text header fallback
            use_link: If True, returns image with 'link' instead of 'id' (for CTA URL).
                     If no public URL available and use_link=True, falls back to text header.

        Returns:
            dict: Header object for WhatsApp API, or None if no header available
        """
        logger.debug(f"_get_interactive_header() called with header_text: {header_text}, use_link: {use_link}")

        # For CTA URL messages, we need a public image URL
        if use_link:
            if self.header_image_url:
                logger.info(f"Using image header with public URL: {self.header_image_url}")
                return {
                    'type': 'image',
                    'image': {'link': self.header_image_url}
                }
            else:
                # CTA URL requires 'link', not 'id' - fall back to text header if no public URL
                if header_text and str(header_text).strip():
                    logger.info(f"CTA URL: no public image URL, falling back to text header: {header_text}")
                    return {
                        'type': 'text',
                        'text': self._truncate(header_text, 60)
                    }
                logger.warning("CTA URL: no public image URL and no header_text - returning None")
                return None

        # For non-CTA messages (buttons, lists), use media ID if available
        media_id = self._get_header_media_id()
        if media_id:
            logger.info(f"Using image header with media ID: {media_id}")
            return {
                'type': 'image',
                'image': {'id': media_id}
            }

        # If no image available, return text header if header_text provided
        if header_text and str(header_text).strip():
            logger.info(f"Falling back to text header: {header_text}")
            return {
                'type': 'text',
                'text': self._truncate(header_text, 60)
            }

        # If nothing available, return None (no header)
        logger.warning("No header available - returning None")
        return None

    @staticmethod
    def _truncate(s, max_len):
        if s is None:
            return None
        s = str(s)
        truncated = s[:max_len]
        if len(s) > max_len:
            logger.debug(f"Truncated string from {len(s)} to {max_len} characters")
        return truncated

    def send_text_message(self, to_phone_number, text):
        """Send a text message via WhatsApp Cloud API"""
        logger.info(f"Sending text message to {to_phone_number}")
        logger.debug(f"Message body: {text[:100]}..." if len(text) > 100 else f"Message body: {text}")
        
        try:
            url = f"{self.api_url}/{self.phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'to': to_phone_number,
                'type': 'text',
                'text': {
                    'body': text
                }
            }
            
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request payload: {json.dumps(data, indent=2)}")
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Text message sent successfully to {to_phone_number}")
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending text message to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Error response: {e.response.text}")
            raise
    
    def send_interactive_buttons(self, to_phone_number, body_text, buttons, header_text="Thaagam Foundation", footer_text=None):
        """Send interactive buttons with optional image header.

        Note: For WhatsApp Cloud interactive messages, the header type 'image' requires
        a published media id. If upload fails, we fall back to text header.
        """
        logger.info(f"Sending interactive buttons to {to_phone_number}")
        logger.debug(f"Body text: {body_text[:100]}..." if len(body_text) > 100 else f"Body text: {body_text}")
        logger.debug(f"Header text: {header_text}")
        logger.debug(f"Buttons: {len(buttons)} buttons")

        try:
            url = f"{self.api_url}/{self.phone_number_id}/messages"

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            interactive_data = {
                'type': 'button',
                'body': {
                    'text': body_text
                },
                'footer': {
                    'text': 'Thaagam Foundation'
                },
                'action': {
                    'buttons': buttons
                }
            }

            header = self._get_interactive_header(header_text, use_link=False)
            if header:
                logger.info(f"Adding header to interactive buttons")
                interactive_data['header'] = header
            else:
                logger.warning("No header available for interactive buttons")

            data = {
                'messaging_product': 'whatsapp',
                'to': to_phone_number,
                'type': 'interactive',
                'interactive': interactive_data
            }

            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request payload: {json.dumps(data, indent=2)}")
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Interactive buttons sent successfully to {to_phone_number}")
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending interactive buttons to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Error response: {e.response.text}")
            raise
            

    def send_interactive_list(self, to_phone_number, body_text, button_text, sections, header_text=None, footer_text="Thaagam Foundation"):
        """Send an interactive list message via WhatsApp Cloud API with optional image header.

        This method also sanitizes/truncates payload fields to avoid Meta Graph API 400s
        caused by invalid lengths/counts.
        """
        logger.info(f"Sending interactive list to {to_phone_number}")
        logger.debug(f"Body text: {body_text[:100]}..." if len(body_text) > 100 else f"Body text: {body_text}")
        logger.debug(f"Button text: {button_text}")
        logger.debug(f"Sections: {len(sections)} sections")
        
        try:
            url = f"{self.api_url}/{self.phone_number_id}/messages"

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            logger.debug("Sanitizing list payload...")
            safe_body_text = self._truncate(body_text, self._BODY_MAX_LEN) or ""
            safe_footer_text = self._truncate(footer_text, 60) or ""
            safe_button_text = self._truncate(button_text, 20) or "Select"

            sanitized_sections = []
            for section_idx, section in enumerate((sections or [])[: self._LIST_MAX_SECTIONS]):
                section_title = self._truncate(section.get('title', ''), self._SECTION_TITLE_MAX_LEN) or ""
                rows = section.get('rows', [])[: self._LIST_MAX_ROWS_PER_SECTION]

                sanitized_rows = []
                for row_idx, row in enumerate(rows):
                    sanitized_rows.append({
                        'id': str(row.get('id', ''))[:200],
                        'title': self._truncate(row.get('title', ''), self._ROW_TITLE_MAX_LEN) or "",
                        'description': self._truncate(row.get('description', ''), self._ROW_DESC_MAX_LEN) or "",
                    })
                    logger.debug(f"Row {row_idx+1}: {sanitized_rows[-1]['title']}")

                sanitized_sections.append({
                    'title': section_title,
                    'rows': sanitized_rows,
                })

            # Ensure at least one row exists (Meta may reject empty sections/rows)
            if not sanitized_sections or not sanitized_sections[0].get('rows'):
                logger.warning("No rows in sections, sending text message instead")
                return self.send_text_message(to_phone_number, "No options available at this time.")

            action = {
                'button': safe_button_text,
                'sections': sanitized_sections
            }

            interactive_data = {
                'type': 'list',
                'body': {
                    'text': safe_body_text
                },
                'footer': {
                    'text': safe_footer_text
                },
                'action': action
            }

            # For interactive lists, try image header first, but fall back to text if that fails
            # Meta sometimes rejects image headers in list messages
            media_id = self._get_header_media_id()
            if media_id:
                logger.info(f"Attempting list with image header (media ID: {media_id})")
                # Try with image header first
                interactive_data['header'] = {
                    'type': 'image',
                    'image': {'id': media_id}
                }

                data = {
                    'messaging_product': 'whatsapp',
                    'to': to_phone_number,
                    'type': 'interactive',
                    'interactive': interactive_data
                }

                logger.debug(f"Request URL: {url}")
                logger.debug(f"Request payload (with image header): {json.dumps(data, indent=2)}")
                
                response = requests.post(url, headers=headers, json=data)

                if response.status_code >= 400:
                    # Image header failed - retry with text header
                    logger.warning(f"Image header failed (status: {response.status_code}), retrying with text header")
                    logger.debug(f"Error response: {response.text}")
                    
                    # Remove the image header and use text header
                    del interactive_data['header']
                    if header_text:
                        interactive_data['header'] = {
                            'type': 'text',
                            'text': self._truncate(header_text, 60)
                        }
                    
                    data = {
                        'messaging_product': 'whatsapp',
                        'to': to_phone_number,
                        'type': 'interactive',
                        'interactive': interactive_data
                    }
                    logger.debug(f"Request payload (with text header): {json.dumps(data, indent=2)}")
                    response = requests.post(url, headers=headers, json=data)

                response.raise_for_status()
            else:
                # No media ID - use text header
                logger.info("No media ID available, using text header")
                if header_text:
                    interactive_data['header'] = {
                        'type': 'text',
                        'text': self._truncate(header_text, 60)
                    }
                    logger.debug(f"Header text: {interactive_data['header']['text']}")

                data = {
                    'messaging_product': 'whatsapp',
                    'to': to_phone_number,
                    'type': 'interactive',
                    'interactive': interactive_data
                }

                logger.debug(f"Request URL: {url}")
                logger.debug(f"Request payload (text header): {json.dumps(data, indent=2)}")
                
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()

            result = response.json()
            logger.info(f"Interactive list sent successfully to {to_phone_number}")
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending interactive list to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Error response: {e.response.text}")
            raise
    
    def send_main_menu(self, phone_number):
        """Send main menu with interactive reply buttons."""
        logger.info(f"Sending main menu to {phone_number}")
        
        buttons = [
            {
                'type': 'reply',
                'reply': {
                    'id': 'donate',
                    'title': 'Donate'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': 'contact',
                    'title': 'Contact'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': 'location',
                    'title': 'Location'
                }
            }
        ]
        
        body_text = "Welcome! How can we help you today?"
        
        logger.debug(f"Main menu buttons: {len(buttons)}")
        return self.send_interactive_buttons(phone_number, body_text, buttons, header_text="Welcome to Thaagam Foundation")

    def send_food_items_interactive(self, phone_number, food_items):
        """Send food items as interactive list with quantity selection"""
        """Send food items as a text-only interactive list."""
        logger.info(f"Sending food items list to {phone_number}")
        logger.debug(f"Number of food items: {len(food_items) if food_items else 0}")
        
        if not food_items:
            logger.warning("No food items available")
            return self.send_text_message(phone_number, "No food items available at this time.")
        
        rows = []
        for item in food_items:
            rows.append({
                'id': f"food_item_{item.id}",
                'title': self._truncate(item.name, self._ROW_TITLE_MAX_LEN),
                'description': self._truncate(f"Rs. {item.price_per_unit}/{item.unit_label}", self._ROW_DESC_MAX_LEN)
            })
            logger.debug(f"Food item: {item.name} - Rs. {item.price_per_unit}/{item.unit_label}")
        
        sections = [{
            'rows': rows
        }]
        
        return self.send_interactive_list(
            phone_number,
            "Select a food item to add to your donation.",
            "View Items",
            sections,
            header_text="Food Donation"
        )

    def send_food_donation_simple_form(self, phone_number, selected_food_item):
        """Send simple step-by-step food donation form as fallback"""
        logger.info(f"Sending food donation simple form to {phone_number}")
        logger.debug(f"Selected food item: {selected_food_item['name']}")
        
        message = f"""
Food Donation Details

Selected Item: {selected_food_item['name']}
Price: Rs. {selected_food_item['price']} per {selected_food_item['unit_label']}

Please provide the following information:

Step 1: Enter Quantity (e.g., 5)
        """
        
        return self.send_text_message(phone_number, message)

    def send_student_list(self, phone_number, students):
        """Send students list with interactive selection"""
        """Send students list as a text-only interactive list."""
        logger.info(f"Sending student list to {phone_number}")
        logger.debug(f"Number of students: {len(students) if students else 0}")
        
        if not students:
            logger.warning("No students available for sponsorship")
            return self.send_text_message(phone_number, "No students available for sponsorship at this time.")
        
        rows = []
        for student in students:
            rows.append({
                'id': f"student_{student.id}",
                'title': self._truncate(student.name, self._ROW_TITLE_MAX_LEN)
            })
            logger.debug(f"Student: {student.name}")


        sections = [{
            'rows': rows
        }]
        
        return self.send_interactive_list(
            phone_number,
            "Select a student to sponsor for their education.",
            "View Students",
            sections,
            header_text="Education Sponsorship"
        )

    def send_patient_list(self, phone_number, patients):
        """Send patients list with interactive selection"""
        """Send patients list as a text-only interactive list."""
        logger.info(f"Sending patient list to {phone_number}")
        logger.debug(f"Number of patients: {len(patients) if patients else 0}")
        
        if not patients:
            logger.warning("No patients need medical assistance")
            return self.send_text_message(phone_number, "No patients need medical assistance at this time.")
        
        rows = []
        for patient in patients:
            rows.append({
                'id': f"patient_{patient.id}",
                'title': self._truncate(patient.name, self._ROW_TITLE_MAX_LEN),
                'description': self._truncate(f"{patient.hospital} | Raised: Rs. {patient.raised_amount:,.0f}", self._ROW_DESC_MAX_LEN)
            })
            logger.debug(f"Patient: {patient.name} - {patient.hospital}")
        
        sections = [{
            'rows': rows
        }]
        
        return self.send_interactive_list(
            phone_number,
            "Select a patient to support with their medical expenses.",
            "View Patients",
            sections,
            header_text="Medical Assistance"
        )

    def send_packages_selection(self, phone_number, packages, selected_items_summary, food_total):
        """Send packages selection with skip option"""
        logger.info(f"Sending packages selection to {phone_number}")
        logger.debug(f"Number of packages: {len(packages) if packages else 0}")
        logger.debug(f"Food total: Rs. {food_total}")
        
        if not packages:
            logger.info("No packages available, continuing without packages")
            return self.send_text_message(
                phone_number,
                f"Packages\n\nNo packages available.\n\n{selected_items_summary}\n\nTotal: Rs. {food_total:,}\n\nType 'continue' to proceed to donor info."
            )
        
        message = f"Step 3: Packages (Optional)\n\n{selected_items_summary}\n\nAvailable Packages:\n\n"
        
        for i, pkg in enumerate(packages, 1):
            message += f"{i}. {pkg.name} - Rs. {pkg.price:,}\n"
            if pkg.description:
                message += f"   {pkg.description}\n"
            message += "\n"
            logger.debug(f"Package {i}: {pkg.name} - Rs. {pkg.price}")
        
        message += "How to select:\n"
        message += "Type package numbers: `1,3` (for packages 1 and 3)\n"
        message += "Type 'skip' to continue without packages\n"
        message += "Type 'continue' to proceed"
        
        return self.send_text_message(phone_number, message)

    def send_donor_info_form(self, phone_number, summary_text):
        """Send donor information collection step by step"""
        logger.info(f"Sending donor info form to {phone_number}")
        logger.debug(f"Summary text: {summary_text[:100]}..." if len(summary_text) > 100 else f"Summary text: {summary_text}")
        
        message = f"Donor Information\n\n{summary_text}\n\nPlease enter your Full Name:"
        return self.send_text_message(phone_number, message)

    # --- CATEGORY & FLOW SENDERS ---
    def send_category_selection(self, phone_number):
        """Send the donation category selection menu."""
        logger.info(f"Sending category selection to {phone_number}")
        
        buttons = [
            {
                'type': 'reply',
                'reply': {
                    'id': 'donate_food',
                    'title': 'Food'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': 'donate_education',
                    'title': 'Education'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': 'donate_medical',
                    'title': 'Medical'
                }
            }
        ]
        
        body_text = """
Choose a Donation Category
        
Your contribution can make a real difference. Please select a cause you wish to support.
        """
        
        logger.debug(f"Category buttons: {len(buttons)}")
        return self.send_interactive_buttons(phone_number, body_text, buttons, header_text="Choose Donation Category")

    def send_donation_flow(
        self, 
        to_phone_number, 
        flow_type='FOOD', 
        flow_id=None, 
        flow_action='data_exchange', 
        flow_action_payload=None):
        """Send the donation flow, specifying the type."""
        logger.info(f"Sending donation flow to {to_phone_number}")
        logger.debug(f"Flow type: {flow_type}")
        logger.debug(f"Flow ID: {flow_id or self.flow_id}")
        
        try:
            url = f"{self.api_url}/{self.phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            flow_token = f"flow_{flow_type.lower()}_{uuid.uuid4().hex[:8]}"
            target_flow_id = flow_id or self.flow_id
            
            logger.debug(f"Flow token: {flow_token}")
            logger.debug(f"Target flow ID: {target_flow_id}")
            
            action_parameters = {
                'flow_cta': 'Donate Now',
                'flow_message_version': '3',
                'flow_token': flow_token,
                'flow_id': target_flow_id,
                'flow_action': flow_action,
                'mode': getattr(settings, 'FLOW_MODE', 'draft'),
            }
            
            if flow_action_payload:
                logger.debug(f"Flow action payload: {json.dumps(flow_action_payload)[:200]}...")
                action_parameters['flow_action_payload'] = flow_action_payload

            interactive_data = {
                'type': 'flow',
                'body': {
                    'text': f'Please complete your {flow_type.lower()} donation by clicking the button below.'
                },
                'action': {
                    'name': 'flow',
                    'parameters': action_parameters
                }
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'to': to_phone_number,
                'type': 'interactive',
                'interactive': interactive_data
            }
            
            logger.info(f"Sending Donation Flow to {to_phone_number}")
            logger.info(f"Flow ID: {target_flow_id}")
            logger.debug(f"Payload: {json.dumps(data, indent=2)}")
            
            response = requests.post(url, headers=headers, json=data)

            # Enhanced error logging
            if response.status_code >= 400:
                logger.error(f"Meta API Error - Status: {response.status_code}")
                logger.error(f"Error Response Body: {response.text}")
                print(f"Meta API Error - Status: {response.status_code}, Body: {response.text}")

            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Donation Flow sent successfully to {to_phone_number}")
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error sending donation flow to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Error Response: {e.response.text}")
                print(f"Error response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in send_donation_flow: {str(e)}", exc_info=True)
            raise
    
    # --- FORM & PAYMENT SENDERS ---
    def send_interactive_cta_url(
        self,
        to_phone_number,
        body_text,
        button_text,
        url,
        header_text="Complete Your Donation"
    ):
        """Send WhatsApp CTA URL interactive message."""
        logger.info(f"Sending CTA URL to {to_phone_number}")
        logger.debug(f"Body text: {body_text[:100]}..." if len(body_text) > 100 else f"Body text: {body_text}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Button text: {button_text}")
        
        try:
            api_url = f"{self.api_url}/{self.phone_number_id}/messages"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "cta_url",
                    "body": {
                        "text": body_text
                    },
                    "footer": {
                        "text": "Thaagam Foundation"
                    },
                    "action": {
                        "name": "cta_url",
                        "parameters": {
                            "display_text": button_text,
                            "url": url
                        }
                    }
                }
            }

            # For CTA URL, use 'link' instead of 'id' for image header
            header = self._get_interactive_header(header_text, use_link=True)
            if header:
                logger.info("Adding header to CTA URL")
                payload['interactive']['header'] = header

            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            response = requests.post(api_url, headers=headers, json=payload)

            if response.status_code >= 400:
                logger.error(f"Error sending CTA URL - Status: {response.status_code}")
                logger.error(f"Error Response: {response.text}")
                print("--- ERROR SENDING CTA URL ---")
                print("Status:", response.status_code)
                print("Response:", response.text)
                print("Payload Sent:", json.dumps(payload, indent=2))
                return None

            result = response.json()
            logger.info(f"CTA URL sent successfully to {to_phone_number}")
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return result

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error sending CTA URL to {to_phone_number}: {str(e)}")
            return None

    def send_payment_redirect(self, phone_number, donation, payment_url):
        """Wrapper for send_interactive_cta_url for payment."""
        logger.info(f"Sending payment redirect to {phone_number}")
        logger.debug(f"Donation amount: Rs. {donation.amount}")
        logger.debug(f"Payment URL: {payment_url}")
        
        body_text = f"Your donation of Rs. {donation.amount:,.0f} is ready. Click below to complete the payment."
        return self.send_interactive_cta_url(phone_number, body_text, "Pay Now", payment_url, header_text="Complete Your Payment")

    def send_donation_form(self, phone_number):
        """Send interactive donation form using buttons and lists"""
        logger.info(f"Sending donation form to {phone_number}")
        
        buttons = [
            {
                'type': 'reply',
                'reply': {
                    'id': 'start_donation',
                    'title': 'Start Donation'
                }
            }
        ]
        
        body_text = """
Donation Form

We'll collect your donation details step by step.

Click the button below to begin:
        """
        
        logger.debug(f"Donation form buttons: {len(buttons)}")
        return self.send_interactive_buttons(phone_number, body_text, buttons, header_text="Donation Form")

    def send_packages_interactive_selection(self, phone_number):
        """Send interactive package selection with buttons"""
        logger.info(f"Sending packages interactive selection to {phone_number}")
        
        # Create package list with buttons
        rows = [
            {
                'id': 'pkg_1',
                'title': 'Birthday Banner',
                'description': 'Rs. 3,000 - Special banner for birthdays',
            }
        ]
        sections = [{'title': 'Optional Packages', 'rows': rows}]
        
        logger.debug(f"Package rows: {len(rows)}")
        return self.send_interactive_list(
            phone_number,
            "Select optional packages to add:",
            "Select Package",
            sections,
            header_text="Add-on Packages"
        )


whatsapp_service = WhatsAppService()