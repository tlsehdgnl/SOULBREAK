# 성당 석재 표면

성당의 석재 네 종은 Poly Haven의 CC0 사진 측량 자료를 사용한다. 색온도와 노멀 강도를 조정했고, 거칠기와 차폐 정보를 머티리얼 패킹 텍스처로 변환했다. [자산 라이선스](https://polyhaven.com/license)

| 에셋 | 제작자 | 게임 내 용도 |
| --- | --- | --- |
| [Rock Tile Floor](https://polyhaven.com/a/rock_tile_floor) | Charlotte Baglioni | 측랑 판석 |
| [Patterned Paving](https://polyhaven.com/a/patterned_paving) | Charlotte Baglioni | 신랑과 성가대석 앞의 돌 포장 |
| [Large Sandstone Blocks](https://polyhaven.com/a/large_sandstone_blocks) | Rob Tuytel | 외벽의 쌓은 사암 |
| [Rock Surface](https://polyhaven.com/a/rock_surface) | Amal Kumar | 기둥, 석상, 아치의 다듬은 돌 |

배포용 Unreal 머티리얼은 프로젝트의 `Content/SoulBreak/Environment`에 들어 있다. 제작 원본을 다시 구울 때 `python Tools/Art/build_chapel_surfaces.py`를 실행한다. Pillow와 NumPy를 사용하며, 처음 실행 시 2K 소스 파일을 받아 `Saved/StoneScans`에 보관하고 SHA-256을 확인한다. 외부 자료의 URL이나 파일 내용이 바뀌면 수동으로 검토한 뒤 해시를 갱신한다.
