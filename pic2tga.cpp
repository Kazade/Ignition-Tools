

#include <cstdint>
#include <boost/program_options.hpp>
#include <fstream>
#include <SOIL/SOIL.h>

typedef uint32_t INT;
typedef uint16_t SHORT;
typedef uint8_t BYTE;

typedef struct PICHeader {
    INT file_size;
    SHORT magic; //Always 38144 (or 0, 149 in separate bytes)
    SHORT width;
    SHORT height;
    SHORT unknown1;
    SHORT unknown2;       
    BYTE unknown3[50];
    SHORT palette_size; //I thought this was palette size - but it's not, it's always 776
    BYTE unknown4[6]; //Always zeros, probably reserved
    BYTE palette[256*3];
    SHORT unknown5; //In one file this was the number of bytes after and including this one, but not in others (??)
    BYTE unknown6[4]; //Seen (0, 0, 1, 0), (4, 0, 1, 0) - probably orientation (e.g flipped image)
} PICHeader;

int main(int argc, char* argv[]) {
    namespace po = boost::program_options;
    
    po::options_description desc("Allowed options");
    desc.add_options()
        ("help", "Produce a help message")
        ("input, i", po::value<std::string>(), "Input filename")
        ("output, o", po::value<std::string>(), "Output filename");

    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, desc), vm);
    po::notify(vm);
   
    if(vm.count("help") || !vm.count("input")) {
        std::cout << "pic2tga --input INPUT [--output OUTPUT]" << std::endl;
        return 1;
    }
    
    std::string input = vm["input"].as<std::string>();
    std::string output = input + ".tga";
    
    std::ifstream file(input.c_str(), std::ios::binary);

    PICHeader header;
    file.read((char*) &header, sizeof(PICHeader));

    if(header.magic != 38144) {
        std::cout << "The specified file is not a valid PIC image" << std::endl;
        return 1;
    }

    std::vector<BYTE> data;
    data.reserve(header.width * header.height * 3);
    for(int i = 0;i < header.width * header.height; ++i) {
        BYTE palette_index;
        file.read((char*)&palette_index, sizeof(BYTE));
        
        for(int j = 0; j < 3; ++j) {
            BYTE c = header.palette[(palette_index * 3) + j];
            data.push_back(c);
        }
    }
    
    SOIL_save_image(output.c_str(), SOIL_SAVE_TYPE_TGA, header.width, header.height, 3, &data[0]);

    return 0;
}
