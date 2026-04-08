"""
STEGOSAURUS WRECKS - Ultimate Steganography Suite
🦕 The most epic steg tool of all time 🦕
"""

import os
import io
import base64
import streamlit as st
from PIL import Image
from typing import Optional

# Import our modules
from steg_core import (
    encode, decode, encode_text, decode_text,
    create_config, calculate_capacity, analyze_image,
    detect_encoding, CHANNEL_PRESETS, StegConfig, EncodingStrategy
)
from crypto import (
    encrypt, decrypt, get_available_methods, crypto_status, HAS_CRYPTO
)
from injector import (
    generate_injection_filename, get_template_names, get_template_info,
    get_jailbreak_template, get_jailbreak_names,
    inject_metadata_pil, inject_text_chunk, read_png_chunks,
    zalgo_text, leetspeak, create_full_injection_package,
    JAILBREAK_TEMPLATES
)

# Page config
st.set_page_config(
    page_title="STEGOSAURUS WRECKS",
    page_icon="🦕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem;
    }
    .steg-box {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #333;
    }
    .capacity-indicator {
        font-family: monospace;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def get_image_download_link(img_bytes: bytes, filename: str) -> str:
    """Generate download link for image bytes"""
    b64 = base64.b64encode(img_bytes).decode()
    return f'<a href="data:image/png;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:#4CAF50;color:white;padding:10px 24px;border:none;border-radius:4px;cursor:pointer;">📥 Download {filename}</button></a>'


def get_file_download_link(data: bytes, filename: str, mime_type: str = "application/octet-stream") -> str:
    """Generate download link for arbitrary file bytes"""
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:{mime_type};base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:#2196F3;color:white;padding:10px 24px;border:none;border-radius:4px;cursor:pointer;">📥 Download {filename}</button></a>'


def load_image(uploaded_file) -> Optional[Image.Image]:
    """Load image from uploaded file or return None"""
    if uploaded_file is not None:
        return Image.open(uploaded_file)
    return None


def image_to_bytes(image: Image.Image) -> bytes:
    """Convert PIL Image to PNG bytes"""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# ============== SIDEBAR ==============
st.sidebar.markdown("# 🦕 STEGOSAURUS WRECKS")
st.sidebar.markdown("*Ultimate Steganography Suite*")
st.sidebar.markdown("---")

# Mode selection
mode = st.sidebar.radio(
    "Select Mode",
    ["🔐 Encode", "🔓 Decode", "🔍 Analyze", "💉 Injector", "⚙️ Settings"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")
crypto_info = crypto_status()
st.sidebar.markdown(f"**Encryption:** {'✅ AES Available' if crypto_info['cryptography_available'] else '⚠️ XOR Only'}")
st.sidebar.markdown(f"**Channels:** {len(CHANNEL_PRESETS)} presets")
st.sidebar.markdown(f"**Bit Depths:** 1-8 bits/channel")

# ============== MAIN CONTENT ==============
st.markdown('<h1 class="main-title">🦕 STEGOSAURUS WRECKS 🦕</h1>', unsafe_allow_html=True)
st.markdown("<p style='text-align:center;font-size:1.2rem;'>S̷̛̤̼̥̹͚͈̓̽̂E̴̳̘͕͍̯̮͖̖͚͋̋͠Ȩ̶͕̪͈̋ͅḌ̴̮͙̯̅̿̈́͐̏ ̷̳̗̟͕͐͂͒̉̑̕T̶̡͖͕̬̺̪̼̂̋̎̾̓͠ͅḪ̷̼͈̝̯̉͆̓̔̒̿̀̈́E̷̝̰͔̺͛̋͌̂̚ ̴̡̡̳̭̹͐̉̈̑F̵̫̜͆́̄͆͑̍́͆͠U̶̪̖̖̻̫͙̓̆̓͜T̵̛͔̭͈̙̙̠̜̤̠̓́́̈̕̕Ȕ̵̜͎̘̞̯͍̦̫͖̆Ŗ̶͍͓̤̪͍̦͔͙̿Ȩ̵͈̹̬͓̝̮̟̎̓͒̀̈́ 🔮</p>", unsafe_allow_html=True)
st.markdown("---")


# ============== ENCODE MODE ==============
if mode == "🔐 Encode":
    st.header("🔐 Encode Data into Image")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📷 Source Image")
        uploaded_image = st.file_uploader(
            "Upload carrier image",
            type=["png", "jpg", "jpeg", "bmp", "gif"],
            help="The image that will carry your hidden data"
        )

        if uploaded_image:
            source_image = Image.open(uploaded_image)
            st.image(source_image, caption=f"Source: {uploaded_image.name}", use_column_width=True)
        else:
            source_image = None
            st.info("👆 Upload an image to get started")

    with col2:
        st.subheader("⚙️ Encoding Configuration")

        # Channel selection
        channel_preset = st.selectbox(
            "Channel Selection",
            list(CHANNEL_PRESETS.keys()),
            index=list(CHANNEL_PRESETS.keys()).index("RGB"),
            help="Which color channels to use for encoding"
        )

        # Bits per channel
        bits_per_channel = st.slider(
            "Bits per Channel",
            min_value=1, max_value=8, value=1,
            help="More bits = more capacity but more visible changes"
        )

        # Bit offset
        bit_offset = st.slider(
            "Bit Offset (0=LSB)",
            min_value=0, max_value=7, value=0,
            help="Which bit position to start encoding at"
        )

        # Compression
        use_compression = st.checkbox("Enable Compression", value=True, help="Compress data before encoding")

        # Strategy
        strategy = st.selectbox(
            "Encoding Strategy",
            ["interleaved", "sequential", "spread", "randomized"],
            help="How to distribute data across pixels"
        )

        # Create config
        config = create_config(
            channels=channel_preset,
            bits=bits_per_channel,
            compress=use_compression,
            strategy=strategy,
            bit_offset=bit_offset
        )

        # Show capacity if image loaded
        if source_image:
            capacity = calculate_capacity(source_image, config)
            st.markdown("### 📊 Capacity")
            st.markdown(f"**Available:** {capacity['human']}")
            st.markdown(f"**Pixels:** {capacity['pixels']:,}")
            st.markdown(f"**Bits/Pixel:** {config.bits_per_pixel}")

    st.markdown("---")

    # Data input section
    st.subheader("📝 Data to Encode")

    data_type = st.radio(
        "Data Type",
        ["Text", "File", "Jailbreak Template"],
        horizontal=True
    )

    payload_data = None
    payload_preview = ""

    if data_type == "Text":
        text_input = st.text_area(
            "Enter text to hide",
            height=150,
            placeholder="Enter your secret message here..."
        )
        if text_input:
            payload_data = text_input.encode('utf-8')
            payload_preview = text_input[:200] + "..." if len(text_input) > 200 else text_input

    elif data_type == "File":
        uploaded_file = st.file_uploader(
            "Upload file to embed",
            type=None,
            help="Any file type - will be compressed and embedded"
        )
        if uploaded_file:
            payload_data = uploaded_file.read()
            payload_preview = f"File: {uploaded_file.name} ({len(payload_data):,} bytes)"

    elif data_type == "Jailbreak Template":
        jb_template = st.selectbox(
            "Select Template",
            get_jailbreak_names(),
            help="Pre-built prompt injection templates"
        )
        jb_text = get_jailbreak_template(jb_template)
        jb_text = st.text_area("Edit Template", jb_text, height=200)
        if jb_text:
            payload_data = jb_text.encode('utf-8')
            payload_preview = jb_text[:200] + "..."

    # Encryption
    st.markdown("---")
    st.subheader("🔒 Encryption (Optional)")

    use_encryption = st.checkbox("Encrypt payload before encoding")
    encryption_password = ""
    encryption_method = "auto"

    if use_encryption:
        col_enc1, col_enc2 = st.columns(2)
        with col_enc1:
            encryption_password = st.text_input("Encryption Password", type="password")
        with col_enc2:
            encryption_method = st.selectbox("Method", get_available_methods())

    # Output filename
    st.markdown("---")
    st.subheader("📁 Output Filename")

    use_injection_filename = st.checkbox("Use Prompt Injection Filename", value=True)

    if use_injection_filename:
        filename_template = st.selectbox(
            "Filename Template",
            get_template_names(),
            help="Pre-built filenames with injection prompts"
        )
        if filename_template == "custom":
            custom_template = st.text_input("Custom Template", "{custom}")
            output_filename = generate_injection_filename("custom", channel_preset, custom_template)
        else:
            output_filename = generate_injection_filename(filename_template, channel_preset)
        st.code(output_filename)
    else:
        output_filename = st.text_input("Output Filename", "encoded_image.png")

    # Metadata injection
    inject_metadata = st.checkbox("Inject metadata hints", value=False)
    metadata_dict = {}
    if inject_metadata:
        metadata_dict["Comment"] = st.text_input("Comment Metadata", f"Decode {channel_preset} LSB")
        metadata_dict["Description"] = st.text_input("Description Metadata", "Contains hidden data")

    # ENCODE BUTTON
    st.markdown("---")

    if st.button("🚀 ENCODE", type="primary", use_container_width=True):
        if not source_image:
            st.error("❌ Please upload a source image!")
        elif not payload_data:
            st.error("❌ Please provide data to encode!")
        else:
            try:
                with st.spinner("Encoding..."):
                    # Encrypt if needed
                    data_to_encode = payload_data
                    if use_encryption and encryption_password:
                        data_to_encode = encrypt(payload_data, encryption_password, encryption_method)
                        st.info("🔐 Data encrypted")

                    # Encode
                    result_image = encode(source_image, data_to_encode, config)

                    # Inject metadata if requested
                    if inject_metadata and metadata_dict:
                        result_image, result_bytes = inject_metadata_pil(result_image, metadata_dict)
                    else:
                        result_bytes = image_to_bytes(result_image)

                st.success("✅ Encoding complete!")
                st.balloons()

                # Display result
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.image(result_image, caption="Encoded Image", use_column_width=True)
                with col_res2:
                    st.markdown("### 📊 Encoding Stats")
                    st.markdown(f"**Payload Size:** {len(payload_data):,} bytes")
                    st.markdown(f"**Channels Used:** {channel_preset}")
                    st.markdown(f"**Bits/Channel:** {bits_per_channel}")
                    st.markdown(f"**Encrypted:** {'Yes' if use_encryption else 'No'}")
                    st.markdown(f"**Compressed:** {'Yes' if use_compression else 'No'}")

                # Download link
                st.markdown(get_image_download_link(result_bytes, output_filename), unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ Encoding failed: {str(e)}")


# ============== DECODE MODE ==============
elif mode == "🔓 Decode":
    st.header("🔓 Decode Data from Image")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📷 Encoded Image")
        uploaded_image = st.file_uploader(
            "Upload image to decode",
            type=["png"],
            help="PNG image with hidden data"
        )

        if uploaded_image:
            source_image = Image.open(uploaded_image)
            st.image(source_image, caption=f"Source: {uploaded_image.name}", use_column_width=True)
        else:
            source_image = None
            st.info("👆 Upload an encoded image")

    with col2:
        st.subheader("⚙️ Decoding Configuration")
        st.warning("⚠️ Configuration must match encoding settings!")

        # Channel selection
        channel_preset = st.selectbox(
            "Channel Selection",
            list(CHANNEL_PRESETS.keys()),
            index=list(CHANNEL_PRESETS.keys()).index("RGB")
        )

        # Bits per channel
        bits_per_channel = st.slider(
            "Bits per Channel",
            min_value=1, max_value=8, value=1
        )

        # Bit offset
        bit_offset = st.slider(
            "Bit Offset",
            min_value=0, max_value=7, value=0
        )

        # Compression
        use_compression = st.checkbox("Data was Compressed", value=True)

        # Strategy
        strategy = st.selectbox(
            "Encoding Strategy",
            ["interleaved", "sequential", "spread", "randomized"],
            key="decode_strategy"
        )

        config = create_config(
            channels=channel_preset,
            bits=bits_per_channel,
            compress=use_compression,
            strategy=strategy,
            bit_offset=bit_offset
        )

    st.markdown("---")

    # Auto-detect option
    auto_detect = st.checkbox("Auto-detect configuration from header", value=True,
                               help="v3.0 encoded images contain config in header")

    # Decryption
    st.subheader("🔓 Decryption (if encrypted)")
    was_encrypted = st.checkbox("Data was encrypted")
    decrypt_password = ""
    if was_encrypted:
        decrypt_password = st.text_input("Decryption Password", type="password")

    # Output format
    output_format = st.radio("Expected Output", ["Text", "Binary File"], horizontal=True)

    # DECODE BUTTON
    if st.button("🔍 DECODE", type="primary", use_container_width=True):
        if not source_image:
            st.error("❌ Please upload an encoded image!")
        else:
            try:
                with st.spinner("Decoding..."):
                    # Decode - use None config for auto-detect
                    decode_config = None if auto_detect else config
                    extracted_data = decode(source_image, decode_config)

                    # Decrypt if needed
                    if was_encrypted and decrypt_password:
                        extracted_data = decrypt(extracted_data, decrypt_password)
                        st.info("🔓 Data decrypted")

                st.success("✅ Decoding complete!")

                if output_format == "Text":
                    try:
                        decoded_text = extracted_data.decode('utf-8')
                        st.subheader("📜 Extracted Text")
                        st.text_area("Decoded Content", decoded_text, height=300)

                        # Copy button
                        st.code(decoded_text)
                    except UnicodeDecodeError:
                        st.warning("⚠️ Could not decode as UTF-8 text. Showing as hex:")
                        st.code(extracted_data.hex())
                else:
                    st.subheader("📦 Extracted Binary Data")
                    st.markdown(f"**Size:** {len(extracted_data):,} bytes")
                    st.markdown(get_file_download_link(extracted_data, "extracted_data.bin"), unsafe_allow_html=True)

                    # Show hex preview
                    st.markdown("**Hex Preview (first 256 bytes):**")
                    st.code(extracted_data[:256].hex())

            except Exception as e:
                st.error(f"❌ Decoding failed: {str(e)}")


# ============== ANALYZE MODE ==============
elif mode == "🔍 Analyze":
    st.header("🔍 Image Analysis")

    uploaded_image = st.file_uploader(
        "Upload image to analyze",
        type=["png", "jpg", "jpeg", "bmp", "gif"]
    )

    if uploaded_image:
        image = Image.open(uploaded_image)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.image(image, caption=uploaded_image.name, use_column_width=True)

        with col2:
            analysis = analyze_image(image)

            st.subheader("📐 Dimensions")
            st.markdown(f"**Width:** {analysis['dimensions']['width']}px")
            st.markdown(f"**Height:** {analysis['dimensions']['height']}px")
            st.markdown(f"**Total Pixels:** {analysis['total_pixels']:,}")
            st.markdown(f"**Mode:** {analysis['mode']}")

        st.markdown("---")
        st.subheader("📊 Channel Analysis")

        for ch_name, ch_data in analysis['channels'].items():
            with st.expander(f"Channel {ch_name}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Mean:** {ch_data['mean']:.2f}")
                    st.markdown(f"**Std Dev:** {ch_data['std']:.2f}")
                    st.markdown(f"**Range:** {ch_data['min']} - {ch_data['max']}")
                with col_b:
                    lsb = ch_data['lsb_ratio']
                    st.markdown(f"**LSB 0s:** {lsb['zeros']*100:.2f}%")
                    st.markdown(f"**LSB 1s:** {lsb['ones']*100:.2f}%")

                    # Suspicious indicator
                    indicator = lsb['chi_square_indicator']
                    if indicator < 0.1:
                        st.success(f"LSB looks natural ({indicator:.3f})")
                    elif indicator < 0.3:
                        st.warning(f"Slight LSB anomaly ({indicator:.3f})")
                    else:
                        st.error(f"Strong LSB anomaly - likely contains data! ({indicator:.3f})")

        st.markdown("---")
        st.subheader("💾 Capacity Estimates")

        for config_name, capacity in analysis['capacity_by_config'].items():
            st.markdown(f"**{config_name}:** {capacity}")

        # PNG Chunks (if PNG)
        if uploaded_image.name.lower().endswith('.png'):
            st.markdown("---")
            st.subheader("📦 PNG Chunks")

            try:
                uploaded_image.seek(0)
                png_bytes = uploaded_image.read()
                chunks = read_png_chunks(png_bytes)

                for chunk in chunks:
                    with st.expander(f"{chunk['type']} ({chunk['length']} bytes)"):
                        st.json(chunk)
            except Exception as e:
                st.warning(f"Could not parse PNG chunks: {e}")
    else:
        st.info("👆 Upload an image to analyze")


# ============== INJECTOR MODE ==============
elif mode == "💉 Injector":
    st.header("💉 Prompt Injection Tools")

    tab1, tab2, tab3 = st.tabs(["📁 Filename Generator", "📝 Jailbreak Templates", "✨ Text Effects"])

    with tab1:
        st.subheader("Injection Filename Generator")

        template_name = st.selectbox(
            "Template",
            get_template_names()
        )

        template_info = get_template_info(template_name)
        if template_info:
            st.info(f"**{template_info['name']}:** {template_info['description']}")

        channels = st.selectbox("Channel String", list(CHANNEL_PRESETS.keys()))

        custom_template = ""
        if template_name == "custom":
            custom_template = st.text_input(
                "Custom Template",
                "my_image_{rand6}_decode_{channels}_lsb_{rand4}"
            )

        if st.button("Generate Filename"):
            filename = generate_injection_filename(template_name, channels, custom_template)
            st.success("Generated filename:")
            st.code(filename)

            # Show multiple variations
            st.markdown("**More variations:**")
            for _ in range(5):
                st.code(generate_injection_filename(template_name, channels, custom_template))

    with tab2:
        st.subheader("Jailbreak Prompt Templates")

        jb_name = st.selectbox(
            "Select Template",
            get_jailbreak_names()
        )

        jb_text = get_jailbreak_template(jb_name)

        st.text_area(
            "Template Content",
            jb_text,
            height=300,
            key="jb_display"
        )

        if st.button("Copy to Clipboard"):
            st.code(jb_text)
            st.success("Template displayed - copy from above!")

        # Full injection package
        st.markdown("---")
        st.subheader("🎁 Full Injection Package")

        package_template = st.selectbox(
            "Filename Template",
            get_template_names(),
            key="pkg_template"
        )
        package_channels = st.selectbox(
            "Channels",
            list(CHANNEL_PRESETS.keys()),
            key="pkg_channels"
        )
        package_text = st.text_area(
            "Payload Text",
            get_jailbreak_template("pliny_classic"),
            height=150,
            key="pkg_text"
        )

        if st.button("Generate Package"):
            package = create_full_injection_package(
                package_text,
                package_template,
                package_channels,
                include_metadata=True
            )
            st.json(package)

    with tab3:
        st.subheader("Text Effect Generator")

        input_text = st.text_input("Input Text", "STEGOSAURUS WRECKS")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Zalgo Text**")
            zalgo_intensity = st.slider("Zalgo Intensity", 1, 5, 3)
            if input_text:
                zalgo_result = zalgo_text(input_text, zalgo_intensity)
                st.text_area("Result", zalgo_result, height=100, key="zalgo_out")

        with col2:
            st.markdown("**Leetspeak**")
            leet_intensity = st.slider("Leet Intensity", 1, 3, 2)
            if input_text:
                leet_result = leetspeak(input_text, leet_intensity)
                st.text_area("Result", leet_result, height=100, key="leet_out")


# ============== SETTINGS MODE ==============
elif mode == "⚙️ Settings":
    st.header("⚙️ Settings & Information")

    st.subheader("🔐 Cryptography Status")
    crypto_info = crypto_status()

    if crypto_info['cryptography_available']:
        st.success("✅ Full cryptography support available (AES-256)")
    else:
        st.warning("⚠️ cryptography library not installed - using XOR fallback")
        st.code("pip install cryptography")

    st.markdown(f"**Available Methods:** {', '.join(crypto_info['available_methods'])}")
    st.markdown(f"**Recommended:** {crypto_info['recommended']}")

    st.markdown("---")
    st.subheader("📊 Channel Presets")

    for name, channels in CHANNEL_PRESETS.items():
        st.markdown(f"**{name}:** {[c.name for c in channels]}")

    st.markdown("---")
    st.subheader("📖 How It Works")

    st.markdown("""
    ### LSB Steganography

    **Least Significant Bit (LSB)** steganography hides data in the least significant bits
    of pixel color values. Since changing the LSB only slightly affects the color
    (by 1 out of 256 levels), the changes are imperceptible to the human eye.

    ### Capacity Calculation

    ```
    Capacity = Width × Height × Channels × BitsPerChannel / 8 bytes
    ```

    For a 1920×1080 image with RGB channels at 1 bit each:
    ```
    1920 × 1080 × 3 × 1 / 8 = 777,600 bytes ≈ 759 KB
    ```

    ### Security Considerations

    - **Detection:** LSB steganography can be detected through statistical analysis
    - **Encryption:** Always encrypt sensitive data before embedding
    - **Compression:** Reduces payload size and adds another layer of obfuscation
    """)

    st.markdown("---")
    st.subheader("🦕 About")

    st.markdown("""
    **STEGOSAURUS WRECKS** - The Ultimate Steganography Suite

    Features:
    - Multi-channel LSB encoding (R, G, B, A and combinations)
    - Variable bit depth (1-8 bits per channel)
    - AES-256 encryption support
    - Zlib compression
    - PNG metadata injection
    - Prompt injection filename generation
    - Jailbreak template library
    - Image analysis tools

    *.-.-.-.-<={LOVE PLINY}=>-.-.-.-.*
    """)


# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#666;'>🦕 STEGOSAURUS WRECKS v2.0 | "
    ".-.-.-.-<={LOVE PLINY}=>-.-.-.-.</p>",
    unsafe_allow_html=True
)
