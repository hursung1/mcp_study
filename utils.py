def get_credential(key):
    """
    .credentials 파일에서 key에 해당하는 api_key를 가져오는 함수
    """

    with open(".credentials", "r") as f:
        lines = f.readlines()

    for line in lines:
        try:
            name, value = line.strip().split("=")
            if name == key:
                return value
        except:
            continue
        
    return None