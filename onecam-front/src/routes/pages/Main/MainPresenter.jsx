import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';
import './Main.css'

const MainPresenter = () => {
  // 상태 관리
  const [prompt, setPrompt] = useState(''); // 프롬프트 입력값
  const [imageList, setImageList] = useState([]); // 감지된 이미지 목록
  const [selectedImagePath, setSelectedImagePath] = useState(null); // 선택된 이미지 경로
  const [responseOutput, setResponseOutput] = useState(''); // 서버 응답 데이터
  const [comfyImage, setComfyImage] = useState([]);

  useEffect(() => {
    // WebSocket 연결 설정
    const socket = io('http://127.0.0.1:5000', {
      transports: ['websocket'], // WebSocket만 사용
    });

    // 서버와 연결되었을 때 실행되는 이벤트
    socket.on('connect', () => {
      console.log('WebSocket 서버에 연결되었습니다');
    });

    // 새로운 이미지가 감지되었을 때 실행되는 이벤트
    socket.on('new_image', (data) => {
        if (data.image_path) {
            console.log('새로운 이미지 감지:', data.image_path);
    
            if (data.image_path.includes('input')) {
              // "input" 경로가 포함된 경우 imageList에 추가
              setImageList((prevList) => [...prevList, data.image_path]);
            } else if (data.image_path.includes('output')) {
              // "output" 경로가 포함된 경우 comfyImage에 저장
              setComfyImage((prevList) => [...prevList, data.image_path]);
            }
          }
    });

    // 서버와 연결이 끊겼을 때 실행되는 이벤트
    socket.on('disconnect', () => {
      console.log('WebSocket 서버와의 연결이 끊어졌습니다');
    });

    return () => {
      socket.disconnect(); // 컴포넌트 언마운트 시 WebSocket 연결 해제
    };
  }, []);

  // 이미지 클릭 시 선택 처리 함수
  const handleSelectImage = async (path) => {
    setSelectedImagePath(path);
    alert(`선택된 이미지: ${path}`);
  };

  // Axios를 사용하여 서버에 데이터 전송
  const handleSend = async () => {
    if (!selectedImagePath) {
      alert('먼저 이미지를 선택해주세요.');
      return;
    }

    if (!prompt) {
      alert('프롬프트를 입력해주세요.');
      return;
    }

    try {
      const res = await axios.post('http://127.0.0.1:5000/send', {
        prompt,
        image_path: selectedImagePath,
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
      setResponseOutput(JSON.stringify(res.data, null, 2)); // 서버 응답 데이터 저장
    } catch (err) {
      console.error(err);
      alert('서버에 데이터를 전송하는 데 실패했습니다.');
    }
  };

  return (
    <div>
      <h1>이미지 경로 감지 및 데이터 전송</h1>

      {/* 프롬프트 입력 */}
      <textarea
        id="promptInput"
        rows="4"
        cols="50"
        placeholder="프롬프트를 입력하세요"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <br />
      <br />

      {/* 데이터 전송 버튼 */}
      <button id="sendRequestBtn" onClick={handleSend}>
        프롬프트와 이미지 경로 전송
      </button>

      {/* 서버 응답 출력 */}
      <div id="responseOutput">
        <pre>{responseOutput}</pre>
      </div>

      {/* 감지된 이미지 목록 */}
      <div className='img-container'>
            <div className='input-img'>
            <h2>감지된 이미지</h2>

                {imageList.map((imagePath, index) => (
                    <div
                    key={index}
                    onClick={() => handleSelectImage(imagePath)}
                    style={{
                    cursor: 'pointer',
                    color: selectedImagePath === imagePath ? 'blue' : 'black',
                    }}
                >
                    {/* <div>{imagePath}</div> */}
                    <img src={imagePath} />
                    </div>
                ))}
                </div>

                <div className='output-img'>
                    <h2>만들어진 이미지</h2>

                    {comfyImage.map((imagePath, index) => (
                        <div
                        key={index}
                        onClick={() => handleSelectImage(imagePath)}
                        style={{
                        cursor: 'pointer',
                        color: selectedImagePath === imagePath ? 'blue' : 'black',
                        }}
                    >
                        {/* <div>{imagePath}</div> */}
                        <img src={imagePath} />
                        </div>
                    ))}
                </div>
        </div>

    </div>
  );
};

export default MainPresenter;