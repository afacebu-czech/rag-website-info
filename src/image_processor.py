"""
Image processing module for extracting text from images (OCR).
Handles livechat inquiries with client names and questions.
"""
import re
from typing import Dict, Optional, Tuple, List
from PIL import Image
import io
import numpy as np

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class ImageProcessor:
    """Process images to extract text and parse client information."""
    
    def __init__(self):
        """Initialize OCR readers with GPU prioritized, CPU as fallback only."""
        self.easyocr_reader = None
        self.use_easyocr = False
        self.use_gpu = False
        
        if EASYOCR_AVAILABLE:
            # ALWAYS try GPU first, only use CPU as fallback
            gpu_attempted = False
            gpu_success = False
            
            # Priority 1: Try GPU initialization first
            try:
                import torch
                
                # Enhanced GPU detection with diagnostics
                gpu_available = torch.cuda.is_available()
                
                if gpu_available:
                    gpu_attempted = True
                    try:
                        # Initialize EasyOCR with GPU for maximum performance
                        self.easyocr_reader = easyocr.Reader(['en'], gpu=True)
                        self.use_gpu = True
                        gpu_success = True
                        device_name = torch.cuda.get_device_name(0)
                        device_count = torch.cuda.device_count()
                        print(f"✅ EasyOCR initialized with GPU: {device_name} (Device {device_count} available)")
                    except Exception as gpu_init_error:
                        print(f"⚠️ EasyOCR GPU initialization failed: {gpu_init_error}")
                        print("🔄 Falling back to CPU...")
                        gpu_success = False
                else:
                    # Enhanced diagnostics for GPU detection failure
                    print("ℹ️ GPU not available via PyTorch CUDA detection")
                    print("   This usually means:")
                    print("   1. PyTorch was installed without CUDA support (CPU-only version)")
                    print("   2. CUDA toolkit is not installed or not in PATH")
                    print("   3. CUDA version mismatch between PyTorch and system")
                    print("   4. NVIDIA drivers need to be updated")
                    print("   💡 To fix: Install PyTorch with CUDA support: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
                    print("   Falling back to CPU...")
            except ImportError:
                print("⚠️ PyTorch not available - cannot check for GPU")
                print("   💡 Install PyTorch: pip install torch")
                gpu_success = False
            except Exception as e:
                if gpu_attempted:
                    print(f"⚠️ EasyOCR GPU initialization failed: {e}")
                    print("🔄 Falling back to CPU...")
                else:
                    print(f"⚠️ GPU check failed: {e}, trying CPU...")
                gpu_success = False
            
            # Priority 2: Only use CPU if GPU initialization failed or GPU not available
            if not gpu_success:
                try:
                    self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                    self.use_easyocr = True
                    self.use_gpu = False
                    print("✅ EasyOCR initialized with CPU (GPU unavailable or failed)")
                except Exception as e2:
                    print(f"❌ EasyOCR CPU initialization also failed: {e2}")
                    self.use_easyocr = False
            else:
                self.use_easyocr = True
        
        if not self.use_easyocr and not TESSERACT_AVAILABLE:
            raise ImportError("Neither EasyOCR nor pytesseract is available. Please install one: pip install easyocr or pip install pytesseract")
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text as string
        """
        try:
            if self.use_easyocr and self.easyocr_reader:
                # EasyOCR processing - convert PIL Image to numpy array
                image_array = np.array(image)
                result = self.easyocr_reader.readtext(image_array)
                # Combine all detected text
                text = " ".join([item[1] for item in result])
                return text.strip()
            elif TESSERACT_AVAILABLE:
                # Tesseract OCR
                text = pytesseract.image_to_string(image, lang='eng')
                return text.strip()
            else:
                raise Exception("No OCR engine available")
        except Exception as e:
            raise Exception(f"Error extracting text from image: {str(e)}")
    
    def detect_multiple_questions(self, text: str) -> List[str]:
        """
        Detect and parse multiple questions from text.
        Handles numbered lists, bulleted lists, and newline-separated questions.
        
        Args:
            text: Text that may contain multiple questions
            
        Returns:
            List of individual questions
        """
        questions = []
        
        # Pattern 1: Numbered questions (1., 2., 3. or 1) 2) 3) or 1- 2- 3-)
        numbered_pattern = r'(?:^|\n)\s*(?:\d+[\.\)\-]\s*)([^\n\d]+?)(?=\n\s*(?:\d+[\.\)\-]|$))'
        numbered_matches = re.findall(numbered_pattern, text, re.MULTILINE | re.IGNORECASE)
        if len(numbered_matches) >= 2:
            questions = [q.strip() for q in numbered_matches if q.strip()]
            return questions
        
        # Pattern 2: Bulleted questions (-, *, •, etc.)
        bulleted_pattern = r'(?:^|\n)\s*[-*•]\s*([^\n]+?)(?=\n\s*[-*•]|$)'
        bulleted_matches = re.findall(bulleted_pattern, text, re.MULTILINE)
        if len(bulleted_matches) >= 2:
            questions = [q.strip() for q in bulleted_matches if q.strip()]
            return questions
        
        # Pattern 3: Question marks as separators (split by ?)
        question_marks = text.count('?')
        if question_marks >= 2:
            # Split by question marks and keep parts that look like questions
            parts = re.split(r'\?+', text)
            questions = [p.strip() + '?' for p in parts if len(p.strip()) > 10]
            if len(questions) >= 2:
                return questions
        
        # Pattern 4: Newline-separated questions (each line that ends with ?)
        lines = text.split('\n')
        question_lines = []
        for line in lines:
            line = line.strip()
            # Skip empty lines, very short lines, or lines that look like headers
            if len(line) > 15 and ('?' in line or line[0].isupper() or any(word in line.lower() for word in ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'do', 'does', 'is', 'are', 'will', 'would'])):
                # Skip if it looks like a title/header (all caps, very short)
                if not (line.isupper() and len(line) < 50):
                    question_lines.append(line)
        
        if len(question_lines) >= 2:
            return question_lines
        
        return []
    
    def parse_client_inquiry(self, text: str) -> Dict[str, Optional[str]]:
        """
        Parse client name and inquiry from extracted text.
        Handles common livechat inquiry formats and multiple questions.
        
        Args:
            text: Extracted text from image
            
        Returns:
            Dictionary with 'client_name', 'inquiry', and 'questions' (list if multiple)
        """
        # Clean up text
        text = text.strip()
        if not text:
            return {"client_name": None, "inquiry": None, "questions": []}
        
        # Common patterns for client names
        name_patterns = [
            r"(?:Hi|Hello|Hey|Dear)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Hi John" or "Hello John Smith"
            r"(?:Name|Client|From):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Name: John Smith"
            r"(?:My name is|I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "My name is John"
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+said",  # "John Smith said"
        ]
        
        client_name = None
        inquiry = text
        
        # Try to extract client name
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client_name = match.group(1).strip()
                # Remove the name part from inquiry
                inquiry = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
                break
        
        # If no name found, try to find first capitalized word sequence
        if not client_name:
            words = text.split()
            # Look for capitalized words at the start
            name_candidates = []
            for word in words[:5]:  # Check first 5 words
                if word and word[0].isupper() and word.isalpha():
                    name_candidates.append(word)
                elif name_candidates:
                    break
            
            if len(name_candidates) >= 1:
                # Take first 1-2 capitalized words as potential name
                client_name = " ".join(name_candidates[:2])
                # Remove name from inquiry
                inquiry = text.replace(client_name, "", 1).strip()
        
        # Clean up inquiry - remove common greetings and filler (but keep questions)
        if inquiry:
            # Remove common greetings at the start
            inquiry = re.sub(r'^(Hi|Hello|Hey|Dear|Good morning|Good afternoon|Good evening)[,.\s]*', '', inquiry, flags=re.IGNORECASE)
            inquiry = re.sub(r'^(My name is|I\'m|I am)\s+[A-Za-z\s]+[,.\s]*', '', inquiry, flags=re.IGNORECASE)
            inquiry = inquiry.strip()
        
        # NEW: Detect multiple questions
        questions_list = self.detect_multiple_questions(inquiry if inquiry else text)
        
        # If multiple questions detected, format them properly
        if questions_list and len(questions_list) >= 2:
            # Format as a structured list of questions
            formatted_questions = "\n\n".join([f"{i+1}. {q}" for i, q in enumerate(questions_list)])
            inquiry = f"The client has asked the following questions:\n\n{formatted_questions}\n\nPlease provide comprehensive answers to all questions."
        elif not inquiry or len(inquiry) < 10:
            # Use full text if it's reasonable length
            if len(text) > 10:
                inquiry = text
            else:
                # If text is also too short, return what we have
                inquiry = text if text else "Could not extract inquiry from image"
        
        return {
            "client_name": client_name if client_name and len(client_name) > 1 else None,
            "inquiry": inquiry if inquiry else text,
            "questions": questions_list  # List of individual questions if multiple detected
        }
    
    def process_image(self, image: Image.Image) -> Dict[str, any]:
        """
        Complete image processing: extract text and parse client info.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with extracted_text, client_name, and inquiry
        """
        try:
            # Extract text
            extracted_text = self.extract_text_from_image(image)
            
            # Parse client information
            parsed_info = self.parse_client_inquiry(extracted_text)
            
            return {
                "extracted_text": extracted_text,
                "client_name": parsed_info["client_name"],
                "inquiry": parsed_info["inquiry"],
                "questions": parsed_info.get("questions", []),  # List of individual questions if multiple
                "has_multiple_questions": len(parsed_info.get("questions", [])) >= 2,
                "success": True
            }
        except Exception as e:
            return {
                "extracted_text": "",
                "client_name": None,
                "inquiry": None,
                "success": False,
                "error": str(e)
            }

