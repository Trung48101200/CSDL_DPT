# Bird Sound CBIR - API Documentation

## Overview
REST API cho hệ thống tìm kiếm âm thanh chim dựa trên đặc điểm (Content-Based Image Retrieval).

**Base URL:** `http://localhost:8000`

**API Prefix:** `/api`

---

## Table of Contents
1. [Audio Endpoints](#audio-endpoints)
   - [List Audio Features](#1-list-audio-features)
   - [Get Audio Feature by ID](#2-get-audio-feature-by-id)
2. [Search Endpoints](#search-endpoints)
   - [Search Similar Sounds](#1-search-similar-sounds)
   - [Health Check](#2-health-check)

---

## Audio Endpoints

### 1. List Audio Features
**Endpoint:** `GET /api/audio`

**Summary:** Lấy danh sách các audio features với phân trang, lọc và sắp xếp

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|------------|
| page | int | 1 | Số trang (bắt đầu từ 1) |
| limit | int | 10 | Số item trên 1 trang (max: 100) |
| label | string | null | Lọc theo mã chim (ví dụ: abhori1, abethr1) |
| filename | string | null | Lọc theo tên file được cắt (ví dụ: XC568398_seg18_m0.wav) |
| original_filename | string | null | Lọc theo tên file gốc (ví dụ: XC568398.ogg) |
| sort_by | string | "created_at" | Trường sắp xếp: `created_at`, `label`, `filename` |
| sort_order | string | "desc" | Thứ tự sắp xếp: `asc` hoặc `desc` |
| search | string | null | Tìm kiếm từ khóa trong filename, original_filename, label |

**Response Model:** `AudioListResponse`
```json
{
  "page": 1,
  "limit": 10,
  "total": 1250,
  "items": [
    {
      "id": 123,
      "filename": "XC568398_seg18_m0.wav",
      "original_filename": "XC568398.ogg",
      "label": "abhori1",
      "duration": 5.12,
      "sample_rate": 32000,
      "energy_mean": 0.245,
      "energy_var": 0.052,
      "zcr_mean": 0.156,
      "zcr_var": 0.043,
      "silence_ratio": 0.15,
      "centroid_mean": 3400.5,
      "centroid_var": 850.3,
      "bandwidth_mean": 2100.0,
      "bandwidth_var": 520.5,
      "rolloff_mean": 5200.0,
      "rolloff_var": 1200.0,
      "harmonic_mean": 0.85,
      "harmonic_var": 0.12,
      "pitch_mean": 2100.0,
      "pitch_var": 450.0,
      "mfcc1_mean": 0.12,
      "mfcc1_var": 0.03,
      "mfcc2_mean": -0.05,
      "mfcc2_var": 0.02,
      "...": "... (mfcc3-13 mean/var omitted for brevity)",
      "mfcc13_mean": 0.01,
      "mfcc13_var": 0.001,
      "created_at": "2026-05-03T10:30:45",
      "updated_at": "2026-05-03T10:30:45"
    }
  ]
}
```

**Example Requests:**

```bash
# Lấy 10 item đầu tiên
curl -X GET "http://localhost:8000/api/audio?page=1&limit=10"

# Lọc theo mã chim
curl -X GET "http://localhost:8000/api/audio?label=abhori1&page=1&limit=20"

# Tìm kiếm từ khóa
curl -X GET "http://localhost:8000/api/audio?search=XC568398&page=1&limit=10"

# Sắp xếp theo label
curl -X GET "http://localhost:8000/api/audio?sort_by=label&sort_order=asc&page=1&limit=10"

# Lọc và tìm kiếm kết hợp
curl -X GET "http://localhost:8000/api/audio?label=abhori1&sort_by=created_at&sort_order=desc&page=1&limit=20"
```

**Frontend Implementation (JavaScript):**
```javascript
async function listAudioFeatures(page = 1, limit = 10, filters = {}) {
  const params = new URLSearchParams({
    page,
    limit,
    ...filters // label, filename, original_filename, sort_by, sort_order, search
  });
  
  const response = await fetch(`/api/audio?${params.toString()}`);
  return await response.json();
}

// Usage
const data = await listAudioFeatures(1, 10, {
  label: 'abhori1',
  sort_by: 'created_at',
  sort_order: 'desc'
});
```

---

### 2. Get Audio Feature by ID
**Endpoint:** `GET /api/audio/{audio_id}`

**Summary:** Lấy thông tin chi tiết của một audio feature theo ID

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|------------|
| audio_id | int | ID của audio feature |

**Response Model:** `AudioFeatureResponse`
```json
{
  "id": 123,
  "filename": "XC568398_seg18_m0.wav",
  "original_filename": "XC568398.ogg",
  "label": "abhori1",
  "duration": 5.12,
  "sample_rate": 32000,
  "energy_mean": 0.245,
  "energy_var": 0.052,
  "zcr_mean": 0.156,
  "zcr_var": 0.043,
  "silence_ratio": 0.15,
  "centroid_mean": 3400.5,
  "centroid_var": 850.3,
  "bandwidth_mean": 2100.0,
  "bandwidth_var": 520.5,
  "rolloff_mean": 5200.0,
  "rolloff_var": 1200.0,
  "harmonic_mean": 0.85,
  "harmonic_var": 0.12,
  "pitch_mean": 2100.0,
  "pitch_var": 450.0,
  "mfcc1_mean": 0.12,
  "mfcc1_var": 0.03,
  "...": "mfcc2-13 mean/var",
  "mfcc13_mean": 0.01,
  "mfcc13_var": 0.001,
  "created_at": "2026-05-03T10:30:45",
  "updated_at": "2026-05-03T10:30:45"
}
```

**Example Requests:**
```bash
# Lấy audio feature với ID 123
curl -X GET "http://localhost:8000/api/audio/123"
```

**Frontend Implementation:**
```javascript
async function getAudioFeature(audioId) {
  const response = await fetch(`/api/audio/${audioId}`);
  return await response.json();
}

// Usage
const audio = await getAudioFeature(123);
console.log(audio.label, audio.duration);
```

---

## Search Endpoints

### 1. Search Similar Sounds
**Endpoint:** `POST /api/search`

**Summary:** Upload file âm thanh và tìm các âm thanh tương đồng trong database

**Request:**
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file` (required, file): Audio file (.wav, .mp3 hoặc .ogg)
  - `top_k` (optional, int, default: 5): Số kết quả trả về (1-20)

**Response Model:** `SearchResponse`
```json
{
  "success": true,
  "query_file": "XC363503_seg6_m0.wav",
  "top_k": 5,
  "processing_time_ms": 245.35,
  "results": [
    {
      "rank": 1,
      "distance": 1.2345,
      "audio_id": 456,
      "filename": "XC363503_seg6_m0.wav",
      "original_filename": "XC363503.ogg",
      "label": "abhori1",
      "duration": 5.12,
      "sample_rate": 32000,
      "common_name": "African Hobby",
      "scientific_name": "Falco cuvierii",
      "summary": "A small falcon found in sub-Saharan Africa...",
      "family": "Falconidae",
      "order": "Falconiformes",
      "genus": "Falco",
      "local_image_path": "bird_images/abhori1.jpg",
      "conservation_status": "Least Concern"
    },
    {
      "rank": 2,
      "distance": 1.5678,
      "audio_id": 789,
      "filename": "XC363503_seg7_m0.wav",
      "original_filename": "XC363503.ogg",
      "label": "abhori1",
      "duration": 4.85,
      "sample_rate": 32000,
      "common_name": "African Hobby",
      "scientific_name": "Falco cuvierii",
      "summary": "A small falcon found in sub-Saharan Africa...",
      "family": "Falconidae",
      "order": "Falconiformes",
      "genus": "Falco",
      "local_image_path": "bird_images/abhori1.jpg",
      "conservation_status": "Least Concern"
    }
    // ... more results
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "query_file": "invalid.wav",
  "top_k": 0,
  "processing_time_ms": null,
  "results": [],
  "message": "File size exceeds maximum allowed size"
}
```

**Example Requests:**

```bash
# Upload single file với 5 kết quả mặc định
curl -X POST "http://localhost:8000/api/search" \
  -F "file=@path/to/audio.wav"

# Upload file với 10 kết quả
curl -X POST "http://localhost:8000/api/search" \
  -F "file=@path/to/audio.wav" \
  -F "top_k=10"

# Upload .mp3 file
curl -X POST "http://localhost:8000/api/search" \
  -F "file=@path/to/audio.mp3" \
  -F "top_k=15"

# Upload .ogg file
curl -X POST "http://localhost:8000/api/search" \
  -F "file=@path/to/audio.ogg" \
  -F "top_k=15"
```

**Frontend Implementation (JavaScript/React):**

```javascript
async function searchSimilarSounds(audioFile, topK = 5) {
  const formData = new FormData();
  formData.append('file', audioFile); // File object from <input type="file">
  formData.append('top_k', topK);
  
  const response = await fetch('/api/search', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

// React Component Example
function SearchComponent() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    setLoading(true);
    try {
      const data = await searchSimilarSounds(file, 10);
      if (data.success) {
        setResults(data.results);
      } else {
        console.error(data.message);
      }
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <input 
        type="file" 
        accept="audio/wav,audio/mpeg,audio/ogg"
        onChange={handleFileUpload}
        disabled={loading}
      />
      {loading && <p>Searching...</p>}
      {results.map(result => (
        <div key={result.audio_id}>
          <p>Rank {result.rank}: {result.common_name}</p>
          <p>Distance: {result.distance.toFixed(4)}</p>
          <img src={result.local_image_path} alt={result.common_name} />
          <p>{result.summary}</p>
        </div>
      ))}
    </div>
  );
}
```

**Python Implementation:**
```python
import requests

def search_similar_sounds(audio_file_path, top_k=5):
    """
    Search for similar bird sounds
    
    Args:
        audio_file_path: Path to audio file (.wav, .mp3, or .ogg)
        top_k: Number of results to return
    
    Returns:
        Search results dictionary
    """
    with open(audio_file_path, 'rb') as f:
        files = {'file': f}
        params = {'top_k': top_k}
        response = requests.post(
            'http://localhost:8000/api/search',
            files=files,
            params=params
        )
    
    return response.json()

# Usage
results = search_similar_sounds('test_audio.wav', top_k=10)
for result in results['results']:
    print(f"Rank {result['rank']}: {result['common_name']} (distance: {result['distance']:.4f})")
```

**Response Field Descriptions:**
| Field | Type | Description |
|-------|------|------------|
| rank | int | Vị trí kết quả (1 là gần nhất) |
| distance | float | Khoảng cách(Euclidean) - càng nhỏ càng tương đồng |
| audio_id | int | ID của audio feature trong database |
| filename | string | Tên file âm thanh được cắt |
| original_filename | string | Tên file âm thanh gốc |
| label | string | Mã chim (ví dụ: abhori1) |
| duration | float | Thời lượng âm thanh (giây) |
| sample_rate | int | Tần số lấy mẫu (Hz) |
| common_name | string | Tên thường gọi của chim |
| scientific_name | string | Tên khoa học |
| summary | string | Mô tả về chim (từ Wikipedia) |
| family | string | Họ (Taxonomy) |
| order | string | Bộ (Taxonomy) |
| genus | string | Giống (Taxonomy) |
| local_image_path | string | Đường dẫn đến hình ảnh chim |
| conservation_status | string | Trạng thái bảo tồn |

---

### 2. Health Check
**Endpoint:** `GET /api/search/health`

**Summary:** Kiểm tra trạng thái của API và các models ML

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "models_loaded": true
}
```

Hoặc khi có vấn đề:
```json
{
  "status": "degraded",
  "version": "1.0.0",
  "database": "disconnected",
  "models_loaded": false
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/search/health"
```

**Frontend Implementation:**
```javascript
async function checkHealth() {
  const response = await fetch('/api/search/health');
  const health = await response.json();
  
  if (health.status === 'healthy') {
    console.log('✓ API is ready to use');
  } else {
    console.warn('⚠ API has issues:', health);
  }
  
  return health;
}
```

---

## Error Handling

**Common Error Codes:**

| Code | Status | Description |
|------|--------|------------|
| 400 | Bad Request | Invalid query parameters |
| 404 | Not Found | Audio feature not found |
| 413 | Payload Too Large | File exceeds size limit |
| 415 | Unsupported Media Type | Invalid file format |
| 500 | Internal Server Error | Server error |

**Error Response Format:**
```json
{
  "detail": "Error message"
}
```

---

## Request/Response Examples

### Example 1: Complete Search Flow

**Step 1: Check API Health**
```bash
curl -X GET "http://localhost:8000/api/search/health"
```

**Step 2: Upload Audio for Search**
```bash
curl -X POST "http://localhost:8000/api/search" \
  -F "file=@bird_sound.wav" \
  -F "top_k=5"
```

**Step 3: View Results**
```javascript
async function fullSearchFlow() {
  // 1. Check health
  const health = await fetch('/api/search/health').then(r => r.json());
  console.log('Health:', health.status);
  
  // 2. Upload file
  const formData = new FormData();
  formData.append('file', audioFile);
  formData.append('top_k', 10);
  
  const results = await fetch('/api/search', {
    method: 'POST',
    body: formData
  }).then(r => r.json());
  
  // 3. Process results
  results.results.forEach(result => {
    console.log(`${result.rank}. ${result.common_name} - Distance: ${result.distance}`);
  });
}
```

### Example 2: Filtering Audio Features

```bash
# Find all abhori1 recordings
curl -X GET "http://localhost:8000/api/audio?label=abhori1&limit=50"

# Search by filename pattern
curl -X GET "http://localhost:8000/api/audio?search=XC568398&limit=20"

# Get recent additions
curl -X GET "http://localhost:8000/api/audio?sort_by=created_at&sort_order=desc&limit=10"
```

---

## Rate Limiting & Constraints

- **File Size Limit:** Kiểm tra `settings.MAX_FILE_SIZE`
- **Allowed Formats:** `.wav`, `.mp3`, `.ogg`
- **Max Results (top_k):** 20
- **Max Items per Page:** 100
- **Default Page Size:** 10

---

## Configuration

**Environment Variables** (from `.env`):
```bash
# API
API_VERSION=1.0.0
TOP_K_RESULTS=5

# Database
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=audio_db

# Server
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB
CLEANUP_UPLOADS=true
```

---

## 📝 Notes for Frontend Development

1. **Always check health endpoint** before performing searches
2. **Use pagination** for listing audio features (avoid loading all at once)
3. **Handle errors gracefully** - display user-friendly messages
4. **Cache results** where possible to reduce API calls
5. **Show processing time** to users during search (see `processing_time_ms`)
6. **Display bird information** from search results (image, name, description)
7. **Consider lazy loading** for long result lists

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-03 | Initial release |

---

**Last Updated:** 2026-05-03  
**API Status:** ✅ Production Ready
